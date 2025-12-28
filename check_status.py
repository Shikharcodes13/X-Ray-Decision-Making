"""Quick status check for X-Ray system."""

from xray.storage_sqlite import SQLiteStorage

print("=" * 60)
print("X-Ray System Status Check")
print("=" * 60)

# Check database
try:
    storage = SQLiteStorage()
    executions = storage.list_executions(10)
    
    print(f"\n[Database] Found {len(executions)} execution(s):")
    for i, exec_data in enumerate(executions, 1):
        exec_id = exec_data["execution_id"]
        steps = exec_data["metadata"].get("total_steps", 0)
        print(f"  {i}. {exec_id[:8]}... ({steps} steps)")
    
    if executions:
        print(f"\n[Dashboard] Access at: http://localhost:5000")
        print(f"  - View all executions: http://localhost:5000")
        print(f"  - View latest execution: http://localhost:5000/execution/{executions[0]['execution_id']}")
    else:
        print("\n[Info] No executions found. Run demo/competitor_selection.py first.")
        
except Exception as e:
    print(f"\n[Error] {e}")

print("\n" + "=" * 60)

