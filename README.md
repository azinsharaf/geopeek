# geopeek

## Running the CLI Script with `arcpy`

To run your CLI script with `arcpy`, which is installed separately via ArcGIS Pro, you need to ensure that your Python environment is set up to use the Python interpreter that comes with ArcGIS Pro. Here's how you can do it:

### Steps to Run Your CLI Script with `arcpy`

1. **Locate ArcGIS Pro Python Environment**: ArcGIS Pro comes with its own Python environment. You need to find the path to this environment. It is typically located in a directory like:

   ```
   C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3
   ```

2. **Activate the ArcGIS Pro Environment**: Open a command prompt or PowerShell and activate the ArcGIS Pro Python environment. You can do this by navigating to the `Scripts` directory of the environment and running the `activate` script:

   ```bash
   cd "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts"
   activate
   ```

3. **Run Your Script**: Once the environment is activated, navigate to your project directory and run your script using the `python -m` command:

   ```bash
   cd path\to\your\project-root
   python -m src.geopeek path/to/your/geodatabase.gdb
   ```

### Alternative: Use a Batch File

If you frequently need to run your script, you can create a batch file to automate the activation and execution process:

1. **Create a Batch File**: Create a new file named `run_geopeek.bat` with the following content:

   ```batch
   @echo off
   call "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\Scripts\activate.bat"
   python -m src.geopeek path/to/your/geodatabase.gdb
   ```

2. **Run the Batch File**: Double-click the batch file to activate the environment and run your script.

By following these steps, you can ensure that your script runs with the correct Python environment that includes `arcpy`.
