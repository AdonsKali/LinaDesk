import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("huggingface_hub is not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
    from huggingface_hub import hf_hub_download

REPO_ID = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
FILE_NAME = "Qwen3-4B-Instruct-2507-Q5_K_S.gguf"
def download_qwen3_model():
    models_dir = project_root / "backend" / "infrastructure" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    repo_id = REPO_ID
    filename = FILE_NAME
    target_model_path = models_dir / filename
    
    print(f"Downloading model to: {models_dir}")
    print(f"File: {filename}")
    
    try:
        downloaded_file = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=models_dir,
            local_dir_use_symlinks=False,
        )
        
        print(f"Model successfully downloaded to: {downloaded_file}")
        print(f"Model location: {target_model_path}")
        
    except Exception as e:
        print(f"Error during model download: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    print("Starting download of Qwen3-4B-Instruct-Q5_K_S model...")
    success = download_qwen3_model()
    
    if success:
        print("\nModel download completed successfully!")
        print("The model is now available for use with the LinaDesk application.")
    else:
        print("\nModel download failed. Please check the error messages above.")
        sys.exit(1)