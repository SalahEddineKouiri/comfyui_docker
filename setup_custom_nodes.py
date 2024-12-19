from typing import List
import sys
import os
import json
from git import Repo, GitCommandError
import subprocess
import wget
import zipfile
import requests

class FileInfo():
    def __init__(self, config) -> None:
        self.file_download_url = config.get("file_download_url", None)
        self.filename = config.get("filename", None)
        self.destination = config.get("destination", None)

class ModelInfo():
    def __init__(self, config: dict) -> None:
        self.model_name = config.get("model_name", None)
        self.model_download_url = config.get("model_download_url", None)
        self.model_filename = config.get("model_filename", None)
        self.model_destination = config.get("destination", None)
        
        self.target_diffusion_model = config.get("target_diffusion_model", None)
        
        self.require_token = config.get("require_token", False)
        self.token = config.get("download_token", None)
        
        self.extra_files = config.get("extra_files", None)
        self.extra_files_lst = []
        if self.extra_files is not None:
            for file_config in self.extra_files:
                self.extra_files_lst.append(
                    FileInfo(file_config)
                )

class Downloader():

    def download_model(self, model: ModelInfo, out_path: str): 
        if model.require_token:
            url = model.model_download_url + f"?token={model.token}"
        else:
            url = model.model_download_url
        
        try:
            filename = wget.download(
                url = url,
                out=out_path
            )
        except:
            filename = self.download_file_with_requests(
                url = url,
                out_path=out_path,
                headers={'User-agent': 'Mozilla/5.0'}
            )
        return True
    
    def download_file_with_requests(self, url, headers, out_path):
        
        local_filename = out_path.split('/')[-1]
        # NOTE the stream=True parameter below
        with requests.get(url, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(out_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    # If you have chunk encoded response uncomment if
                    # and set chunk_size parameter to None.
                    #if chunk: 
                    f.write(chunk)
        return local_filename
    
    def download_file(self, file: FileInfo, out_path: str): 
        url = file.file_download_url
        try:
            filename = wget.download(
                url = url,
                out=out_path
            )
        except:
            filename = self.download_file_with_requests(
                url = url,
                out_path=out_path,
                headers={'User-agent': 'Mozilla/5.0'}
            )
        return True
    
    def setup_model(self, model: ModelInfo):
        
        print(f"Dowloading {model.model_name} ...")
        
        destination = model.model_destination
        if model.target_diffusion_model:
            destination = os.path.join(destination, model.target_diffusion_model)
            
        if not os.path.exists(destination):
            os.makedirs(destination)
        model_path = f"{destination}/{model.model_filename}"
        if not os.path.isfile(model_path): 
            downloaded = self.download_model(model, model_path)
            if model.model_filename.endswith(".zip"):
                print(f"Model {model.model_filename} is a zip file, extracting ...")
                with zipfile.ZipFile(model_path, "r") as zip_ref:
                    zip_ref.extractall(destination)
        if model.extra_files_lst:
            for file in model.extra_files_lst:
                file_path = f"{file.destination}/{file.filename}"
                if not os.path.isfile(file_path):
                    file_downloaded = self.download_file(file, file_path)
                    if file.filename.endswith(".zip"):
                        print(f"File {model.model_filename} is a zip file, extracting ...")
                        with zipfile.ZipFile(file_path, "r") as zip_ref:
                            zip_ref.extractall(file.destination)

class CustomNodesPackage(Downloader):
    def __init__(self, config: dict) -> None:
        super().__init__()
        
        self.models: List[ModelInfo] = []
        self.MODELS_TREE = ['diffusers','checkpoints','configs','upscale_models','style_models','clip','gligen','ipadapter','controlnet','sams','diffusion_models','vae','grounding-dino','unet','photomaker','vae_approx','loras','clip_vision','embeddings','hypernetworks']
        self.model_destination = "models"
        if not os.path.exists(f"{self.model_destination}/"):
            os.makedirs(f"{self.model_destination}/")
        self.setup_models_dir()
        
        self.package_destination = "custom_nodes"
        if not os.path.exists(f"{self.package_destination}/"):
            os.makedirs(f"{self.package_destination}/")
            
        self.package_name = config.get("custom_node_name", None)
        self.package_git_repo = config.get("custom_node_git_repo", None)
        
        self.extras = config.get("extras", None)
        if self.extras is not None:
            models = self.extras.get("models", None)
            if models is not None:
                for model_config in models:
                    self.models.append(
                        ModelInfo(model_config)
                    )
        
    def setup_models_dir(self):
        for dir in self.MODELS_TREE:
            tree_path = f"models/{dir}/"
            if not os.path.exists(tree_path):
                os.makedirs(tree_path)   
                    
    def clone_from_git(self):
        repo = Repo.clone_from(
            url=self.package_git_repo,
            to_path=f"{self.package_destination}/{self.package_name}"
        )
        return True
    
    def clone_or_update_repo(self):
        """
        Clone a Git repository if it doesn't exist locally, or update it if it does.
        """
        
        repo_url = self.package_git_repo
        local_path = f"{self.package_destination}/{self.package_name}"
        try:
            if os.path.exists(local_path) and os.path.isdir(local_path):
                # Check if the directory is a valid git repo
                try:
                    repo = Repo(local_path)
                    if repo.remotes.origin.url == repo_url:
                        print(f"Repository already exists at {local_path}. Pulling updates...")
                        repo.remotes.origin.pull()
                        return True
                    else:
                        print(f"Different repository exists at {local_path}.")
                        return False
                except GitCommandError as e:
                    print(f"Error: {e}")
                    return False
            else:
                # Clone the repository if it doesn't exist
                print(f"Cloning repository from {repo_url} to {local_path}...")
                Repo.clone_from(repo_url, local_path)
                return True
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return False
    
    def restart_comfy(self, comfy):
        pass
    
    def setup(self):
        print(f"Cloning {self.package_name} to {self.package_destination}/{self.package_name} ...")
        cloned = self.clone_or_update_repo()
        rqmnt_path = f"{self.package_destination}/{self.package_name}/requirements.txt"
             
        if cloned:
            if os.path.isfile(rqmnt_path):
                subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", rqmnt_path, "--no-cache-dir"])
        
        print(f"Found {len(self.models)} models:")
        for model in self.models:
            self.setup_model(model)
                          
        print(f"Finished {self.package_name} setup")
        
        
if __name__ == "__main__":
    with open("custom_models.json", "r") as model_config_file:
        model_config = json.load(model_config_file)
    
    downloader = Downloader()    
    print(f"Found {len(model_config)} models in config...")
    for model in model_config:
        model = ModelInfo(model)
        downloader.setup_model(model)
        
    
    with open("custom_node_config.json", "r") as config_file:
        config = json.load(config_file)

    print(f"Found {len(config)} custom packages in config...")
    for cstm_pkg in config:    
        custom_package = CustomNodesPackage(cstm_pkg)
        custom_package.setup()
        
    