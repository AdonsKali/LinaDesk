import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("huggingface_hub is not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
    from huggingface_hub import snapshot_download


def download_qwen3_model():
    models_dir = project_root / "backend" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading model to: {models_dir}")
    repo_id = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
    try:
        downloaded_dir = snapshot_download(
            repo_id=repo_id,
            allow_patterns=["*Q4_K_M.gguf", "*q4_k_m.gguf", "*.gguf"],  # Download GGUF quantized models
            local_dir=models_dir,
            local_dir_use_symlinks=False,
            resume_download=True
        )
        
        print(f"Model successfully downloaded to: {downloaded_dir}")
        gguf_files = list(models_dir.rglob("*.gguf"))
        
        if gguf_files:
            # Take the first (or most likely the only) GGUF file that was downloaded
            source_model_path = gguf_files[0]
            
            # Target path for the model (as expected by the project)
            target_model_path = models_dir / "model.gguf"
            
            # If the target name is not already "model.gguf", rename it
            if source_model_path.name != "model.gguf":
                import shutil
                shutil.copy2(source_model_path, target_model_path)
                print(f"Copied model to standard name: {target_model_path}")
            else:
                print(f"Model already named as expected: {source_model_path}")
                
            print(f"Download completed successfully!")
            print(f"Model location: {target_model_path}")
        else:
            print("Warning: No .gguf files found in the downloaded directory.")
        
    except Exception as e:
        print(f"Error during model download: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    print("Starting download of Qwen3-4B-Instruct model...")
    success = download_qwen3_model()
    
    if success:
        print("\nModel download completed successfully!")
        print("The model is now available for use with the LinaDesk application.")
    else:
        print("\nModel download failed. Please check the error messages above.")
        sys.exit(1)