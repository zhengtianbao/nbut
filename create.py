import requests
import base64
import json
import argparse
import subprocess
import tempfile
import os

# 基本配置
BASE_URL = "http://192.168.122.43:3000/api/v1"
ACCESS_TOKEN = "1d195256944cb2d0a77ea30df1cab3574cde3d42"  # 替换为您的 Access Token

# 创建用户（需要管理员权限）
def create_user(username, email, password, name=None):
    url = f"{BASE_URL}/admin/users"
    headers = {"Content-Type": "application/json",
               "Authorization": "token " + ACCESS_TOKEN }
    data = {
        "username": username,
        "email": email,
        "password": password,
        "name": name or username
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print(f"用户 {username} 创建成功")
        return response.json()
    else:
        print(f"用户 {username} 创建失败: {response.text}")
        return None

# 创建仓库
def create_repo(username, repo_name, private=False):
    url = f"{BASE_URL}/admin/users/{username}/repos"
    headers = {"Content-Type": "application/json",
               "Authorization": "token " + ACCESS_TOKEN }
    data = {
        "name": repo_name,
        "description": f"{username} 的仓库",
        "private": private
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print(f"仓库 {repo_name} 创建成功")
        return response.json()
    else:
        print(f"仓库 {repo_name} 创建失败: {response.text}")
        return None

# 初始化仓库文件
def init_repo_file(owner, repo, file_path, content, message="Initial commit"):
    url = f"{BASE_URL}/repos/{owner}/{repo}/contents/{file_path}"
    headers = {"Content-Type": "application/json",
               "Authorization": "token " + ACCESS_TOKEN }
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    data = {
        "content": encoded_content,
        "message": message
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print(f"文件 {file_path} 初始化成功")
    else:
        print(f"文件 {file_path} 初始化失败: {response.text}")

# 更新 ArgoCD 账户密码
def update_argocd_password(username, password):
    try:
        command = [
            "argocd", 
            "account", 
            "update-password", 
            "--account", username, 
            "--current-password", "gZsw9aXvR3magjO5", 
            "--new-password", password
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"ArgoCD 账户 {username} 密码更新成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ArgoCD 账户 {username} 密码更新失败: {e.stderr}")
        return False

# 创建 Kubernetes 命名空间和 ResourceQuota
def create_k8s_namespace_and_quota(username):
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_file_name = temp_file.name
            # 写入 YAML 内容
            yaml_content = f"""apiVersion: v1
kind: Namespace
metadata:
  name: "{username}"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  namespace: "{username}"
  name: "{username}"
spec:
  hard:
    nvidia.com/gpu: "2"
    requests.cpu: "2"
    requests.memory: "2Gi"
    limits.cpu: "2"
    limits.memory: "2Gi"
"""
            temp_file.write(yaml_content)
            
        # 使用临时文件执行 kubectl 命令
        process = subprocess.run(
            ["kubectl", "apply", "-f", temp_file_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        # 删除临时文件
        os.unlink(temp_file_name)
        
        print(f"Kubernetes 命名空间和 ResourceQuota 创建成功: {username}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Kubernetes 命名空间和 ResourceQuota 创建失败: {e.stderr}")
        # 如果出错，也需要清理临时文件
        if 'temp_file_name' in locals():
            try:
                os.unlink(temp_file_name)
            except:
                pass
        return False

# 创建 ArgoCD 项目
def create_argocd_project(username):
    try:
        command = [
            "argocd", 
            "proj", 
            "create", 
            username,
            "-d", f"https://kubernetes.default.svc,{username}",
            "--src", f"http://192.168.122.43:3000/{username}/demo.git"
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"ArgoCD 项目 {username} 创建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ArgoCD 项目 {username} 创建失败: {e.stderr}")
        return False

# 创建 ArgoCD 应用
def create_argocd_application(username):
    try:
        command = [
            "argocd", 
            "app", 
            "create", 
            username,
            "--repo", f"http://192.168.122.43:3000/{username}/demo.git",
            "--path", "deploy",
            "--dest-server", "https://kubernetes.default.svc",
            "--dest-namespace", username,
            "--project", username,
            "--sync-policy", "automated",
            "--auto-prune",
            "--allow-empty",
            "--self-heal"
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"ArgoCD 应用 {username} 创建成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ArgoCD 应用 {username} 创建失败: {e.stderr}")
        return False

# 解析命令行参数
def parse_arguments():
    parser = argparse.ArgumentParser(description='创建Gitea用户和仓库')
    parser.add_argument('--username', required=True, help='用户名')
    parser.add_argument('--email', required=True, help='邮箱')
    parser.add_argument('--password', required=True, help='密码')
    parser.add_argument('--name', help='显示名称（可选，默认与用户名相同）')
    return parser.parse_args()

# 主程序
def main():
    # 解析命令行参数
    args = parse_arguments()
    
    # 获取用户信息
    username = args.username
    email = args.email
    password = args.password
    name = args.name
    
    # 需要初始化的文件内容
    initial_files = {
        "README.md": "# Welcome to your repository\nThis is an initial file.",
        ".gitignore": "*.log",
        "deploy/deployment.yaml": f"""apiVersion: v1
kind: Pod
metadata:
  name: demo
spec:
  restartPolicy: Never
  containers:
    - name: cuda-vectoradd
      image: nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda11.7.1-ubuntu20.04
      env:
      - name: GPU_CORE_UTILIZATION_POLICY
        value: force
      - name: NVIDIA_VISIBLE_DEVICES
        value: none
      resources:
        limits:
          cpu: "1"
          memory: "2048Mi"
          nvidia.com/gpu: 1
          nvidia.com/gpumem: 8000
          nvidia.com/gpucores: 30
"""
    }
    
    # 创建用户（需要管理员权限）
    user_info = create_user(username, email, password, name)
    if not user_info:
        return
    
    # 为用户创建仓库
    repo_name = "demo"
    repo_info = create_repo(username, repo_name, private=False)
    if not repo_info:
        return
    
    # 初始化仓库文件
    for file_path, content in initial_files.items():
        init_repo_file(username, repo_name, file_path, content)
    
    # 更新 ArgoCD 账户密码
    update_argocd_password(username, password)
    
    # 创建 Kubernetes 命名空间和 ResourceQuota
    create_k8s_namespace_and_quota(username)
    
    # 创建 ArgoCD 项目
    create_argocd_project(username)
    
    # 创建 ArgoCD 应用
    create_argocd_application(username)

if __name__ == "__main__":
    main()
