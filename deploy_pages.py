import os, shutil, subprocess

repo = r"c:\Users\17197\ComateProjects\comate-zulu-demo"
docs = os.path.join(repo, "docs")

# 1. Save docs to temp
tmp = os.path.join(repo, "_tmp_docs")
if os.path.exists(tmp):
    shutil.rmtree(tmp)
shutil.copytree(docs, tmp)

# 2. Checkout gh-pages
subprocess.run(["git", "checkout", "gh-pages"], cwd=repo, check=True)

# 3. Remove everything except .git
for item in os.listdir(repo):
    if item == ".git":
        continue
    path = os.path.join(repo, item)
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)

# 4. Copy docs contents to root
for item in os.listdir(tmp):
    src = os.path.join(tmp, item)
    dst = os.path.join(repo, item)
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

# 5. Commit and push
subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
subprocess.run(["git", "commit", "-m", "deploy: 5月11日日报"], cwd=repo, check=True)
subprocess.run(["git", "push", "-f", "origin", "gh-pages"], cwd=repo, check=True)

# 6. Back to master
subprocess.run(["git", "checkout", "master"], cwd=repo, check=True)

# 7. Cleanup
shutil.rmtree(tmp)
print("Deployed successfully!")
