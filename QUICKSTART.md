# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Run the Demo

Open a terminal and run:

```bash
python demo/competitor_selection.py
```

This will:
- Execute a competitor selection workflow
- Save execution data to `xray.db`
- Print the execution ID

Example output:
```
🔍 Running Competitor Selection Workflow...
Reference Product: Stainless Steel Water Bottle 32oz Insulated

✅ Execution ID: abc123-def456-...
✅ Selected Competitor: HydroFlask 32oz Wide Mouth
   Price: $44.99
   Rating: 4.5★
   Reviews: 8932

📊 View in dashboard: http://localhost:5000/execution/abc123-def456-...
```

## 3. Start the Dashboard

In a new terminal, run:

```bash
python xray/dashboard/app.py
```

Then open your browser to: **http://localhost:5000**

You'll see:
- A list of all executions
- Click any execution to see detailed step-by-step information

## 4. Using X-Ray in Your Own Code

```python
from xray import XRay, Storage

# Initialize storage
storage = Storage()

# Create an execution context
with XRay(storage=storage) as xray:
    # Record steps as your workflow progresses
    xray.record_step(
        step_name="my_step",
        input_data={"key": "value"},
        output_data={"result": "data"},
        reasoning="Why this decision was made"
    )
    
    # More steps...
    xray.record_step(
        step_name="another_step",
        input_data={"input": "data"},
        output_data={"output": "result"},
        reasoning="Another decision point"
    )

# Execution is automatically saved when exiting the context
```

## Next Steps

- Read the full [README.md](README.md) for architecture details
- Explore the demo code in `demo/competitor_selection.py`
- Customize the dashboard templates in `xray/dashboard/templates/`

