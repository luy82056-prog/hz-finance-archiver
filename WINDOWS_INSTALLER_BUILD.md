# Windows 安装包生成说明

普通用户最终应该拿到这个文件：

```text
HZ财务归档器-Windows安装包.exe
```

这个文件在 Windows 电脑上双击即可出现安装向导，不需要用户打开 PowerShell。

## 为什么当前 macOS 不能直接生成

Windows 安装包需要 Windows 版 PyInstaller 生成 `.exe`，再由 Inno Setup 打成安装器。PyInstaller 不能在 macOS 上可靠交叉编译 Windows `.exe`，所以最终 Windows 安装包必须在 Windows 环境生成。

## 推荐方式：GitHub Actions 自动生成

项目里已经加入：

```text
.github/workflows/build-windows-installer.yml
```

把项目上传到 GitHub 后：

1. 打开 GitHub 仓库。
2. 进入 `Actions`。
3. 选择 `Build Windows Installer`。
4. 点击 `Run workflow`。
5. 等待完成后，在 `Artifacts` 下载：

```text
HZ财务归档器-Windows安装包.exe
```

下载到这个 `.exe` 后，就可以发给其他 Windows 电脑直接双击安装。

## 本地 Windows 电脑生成

如果不用 GitHub Actions，可以在 Windows 10/11 电脑上：

1. 安装 Python 3.10 或更高版本。
2. 安装 Inno Setup 6。
3. 先把整个 zip 解压到桌面，不要在压缩包窗口里直接双击。
4. 双击 `Build-Windows-Setup.cmd`。
5. 如果失败，窗口不会立即消失，完整日志在 `build_installer.log`。
6. 生成结果在：

```text
installer_output\HZ财务归档器-Windows安装包.exe
```
