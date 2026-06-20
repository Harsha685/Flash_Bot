from enum import Enum
from flasher import get_flasher
from flashbot.tester.test_cases import get_tests_for_sketch
from flashbot.tester.test_runner import TestRunner
from flashbot.logger.result_store import save_result

class PipelineState(Enum):
    IDLE     = "idle"
    DETECTED = "detected"
    BUILDING = "building"
    FLASHING = "flashing"
    TESTING  = "testing"
    DONE     = "done"
    FAILED   = "failed"

TRANSITIONS = {
    PipelineState.IDLE:     [PipelineState.DETECTED],
    PipelineState.DETECTED: [PipelineState.BUILDING],
    PipelineState.BUILDING: [PipelineState.FLASHING, PipelineState.FAILED],
    PipelineState.FLASHING: [PipelineState.TESTING,  PipelineState.FAILED],
    PipelineState.TESTING:  [PipelineState.DONE,     PipelineState.FAILED],
    PipelineState.DONE:     [PipelineState.IDLE],
    PipelineState.FAILED:   [PipelineState.IDLE],
}

class PipelineStateMachine:

    def __init__(self, on_state_change=None, on_test_result=None):
        self.state = PipelineState.IDLE
        # optional callbacks for UI layer
        self.on_state_change = on_state_change or (lambda old, new: print(f"[STATE] {old.value} → {new.value}"))
        self.on_test_result = on_test_result or (lambda passed, results: None)

    def transition(self, new_state: PipelineState):
        allowed = TRANSITIONS.get(self.state, [])
        if new_state not in allowed:
            raise RuntimeError(
                f"Illegal transition: {self.state.value} → {new_state.value}"
            )
        self.on_state_change(self.state, new_state)
        self.state = new_state

    def run(self, device, sketch_path: str):
        flash_status = "failed"
        flash_error = None
        source_hash = None

        try:
            self.transition(PipelineState.DETECTED)
            flasher = get_flasher(device.fqbn)

            self.transition(PipelineState.BUILDING)
            if not flasher.build(sketch_path):
                self.transition(PipelineState.FAILED)
                flash_error = "Build failed"
                return

            self.transition(PipelineState.FLASHING)
            if not flasher.flash(device.port, sketch_path):
                self.transition(PipelineState.FAILED)
                flash_error = "Flash failed"
                return

            flash_status = "success"

            self.transition(PipelineState.TESTING)
            tests = get_tests_for_sketch(sketch_path)
            if tests:
                runner = TestRunner(device.port)
                all_passed, results = runner.run_all(tests)
                self.on_test_result(all_passed, results)

            self.transition(PipelineState.DONE)

        except Exception as e:
            flash_error = str(e)
            if self.state not in (PipelineState.DONE, PipelineState.FAILED):
                self.state = PipelineState.FAILED
            print(f"[ERROR] {e}")

        finally:
            save_result(device.name, device.fqbn, device.port,
                        sketch_path, flash_status, flash_error, source_hash)
            self.state = PipelineState.IDLE