# app.py

import debugpy

from fileops.processor import FileProcessor

## Start the debug server on port 5678
# debugpy.listen(("0.0.0.0", 5678))
# print("Waiting for debugger to attach...")
# debugpy.wait_for_client()  # Optional: wait for the debugger to attach


if __name__ == "__main__":
    print('Startup MEAexplorer!')
    CONFIG_PATH = "data/config.yaml"
    processor = FileProcessor(CONFIG_PATH)
    processor.load_and_process_files()
    print('All operations finished.')