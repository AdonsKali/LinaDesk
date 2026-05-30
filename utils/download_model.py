import sys
from pathlib import Path
from argparse import ArgumentParser

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("huggingface_hub is not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub"])
    from huggingface_hub import hf_hub_download
def download_model(repo_id, file_name):
    models_dir = project_root / "backend" / "infrastructure" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    target_model_path = models_dir / file_name
    
    print(f"Downloading model to: {models_dir}")
    print(f"File: {file_name}")
    
    try:
        downloaded_file = hf_hub_download(
            repo_id=repo_id,
            filename=file_name,
            local_dir=models_dir,
        )
        
        print(f"Model successfully downloaded to:\n {downloaded_file}\n")
        print(f"Model location: {target_model_path}")
        
    except Exception as e:
        print(f"Error during model download: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    print("Starting download of LLM model...")
    parser = ArgumentParser()

    parser.add_argument("-repo_id", "--repo_id", type=str, required=True, 
                       help="Hugging Face repository ID")
    parser.add_argument("-file_name", "--file_name", type=str, required=True,
                       help="Model file name to download")
    args = parser.parse_args()
    success = download_model(args.repo_id, args.file_name)
    
    if success:
        print("\nModel download completed successfully!")
        print("The model is now available for use with the LinaDesk application.")
    else:
        print("\nModel download failed. Please check the error messages above.")
        sys.exit(1)