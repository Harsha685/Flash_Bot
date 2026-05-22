from logger.result_store import get_results, init_db
import datetime

def print_history():
    rows = get_results()
    
    if not rows:
        print("No flash runs found.")
        return
    
    print(f"{'ID':<<5} {'Board':<<25} {'FQBN':<<35} {'Sketch':<<30} {'Status':<<10} {'Timestamp'}")
    print("-" * 120)
    for row in rows:
        status_str = "SUCCESS" if row[5] == "success" else "FAILED"
        print(f"{row[0]:<<5} {row[1]:<<25} {row[2]:<<35} {row[4]:<<30} {status_str:<10} {row[7]}")

def print_failures(days=7):
    rows = get_results()
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    
    failed = []
    for row in rows:
        if row[5] == "failed":
            ts = datetime.datetime.strptime(row[7], "%Y-%m-%d %H:%M:%S")
            if ts > since:
                failed.append(row)
    
    if not failed:
        print(f"No failed runs in the last {days} days.")
        return
    
    print(f"{'ID':<<5} {'Board':<<25} {'Sketch':<<30} {'Error':<<40} {'Timestamp'}")
    print("-" * 120)
    for row in failed:
        print(f"{row[0]:<<5} {row[1]:<<25} {row[4]:<<30} {str(row[6] or ''):<<40} {row[7]}")

if __name__ == "__main__":
    init_db()
    print_history()
    print()
    print_failures()
    