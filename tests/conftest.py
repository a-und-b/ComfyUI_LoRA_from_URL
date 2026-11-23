import os, sys, tempfile, types
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if "folder_paths" not in sys.modules:
    fp = types.ModuleType("folder_paths")
    fp.get_input_directory = lambda: tempfile.mkdtemp()
    sys.modules["folder_paths"] = fp
if "comfy" not in sys.modules:
    comfy = types.ModuleType("comfy")
    comfy.utils = types.ModuleType("comfy.utils")
    comfy.sd = types.ModuleType("comfy.sd")
    sys.modules.update({"comfy": comfy, "comfy.utils": comfy.utils, "comfy.sd": comfy.sd})
