运行环境、隐私与互通
====================

录制：框选范围后，先选择输出 GIF 才开始捕获；取消不会启动录制。影格由后台线程逐张写入，队列上限为三张与 64 MiB，单张超限会拒绝。队列已满时跳过捕获，并保留实际经过的播放时间。仍保留帧率、时长、影格数上限与摄像头画中画。停止后异步完成写入，只有成功时才原子替换目标；取消与写入失败会清除临时文件，保留已有目标文件。

手机控制：Settings → Remote control 只提供 HTTPS，令牌每次启动都会更换，可执行动作采用固定列表。手机不会自动信任本机自签名证书。请先导出公开证书，比对显示的 SHA-256 指纹，再依手机或浏览器设置导入或信任。私钥留在用户数据目录。IP 更改、到期或重新生成证书时，可能需要信任新证书。TLS 启动失败不会退回 HTTP。

画面文字：Tools → Read text 优先使用本机 OCR：Windows 的 Windows.Media.Ocr、macOS 的 Vision，或已安装且具有语言数据的 Tesseract 可执行文件。本机提取文字不需要云端同意或 ANTHROPIC_API_KEY；成功但没有文字时不会上传截图。翻译与提问只有在另行同意发送文字且提供密钥时，才会将识别文字发送至 Anthropic。本机失败后的截图回退需要独立的画面发送同意与密钥。结果会显示后端及错误，也能撤回同意。

Puppet 宠物：安装可选的 puppet extra 与可用的 Imervue runtime，再于宠物页选择或拖入原始 Imervue .puppet v1 文件。已有图片与 sprite 宠物包仍可使用。Puppet 宠物使用 Imervue 画布、动作与表情，可复制或关闭，并支持 FrontEngine 覆盖层控制与预设集。可另选 .petscript.json 使用 Imervue 原有脚本引擎；FrontEngine pet.json 宠物包不是 puppet 文件。未知版本、不安全的归档路径与无效资源会在加载 runtime 前拒绝。

场景：场景页支持旧 entry mapping JSON、有版本的 frontengine.scene envelope，以及便携式 .fescene 包。PUPPET 项目可设置位置、大小、不透明度、有限数值参数，以及可选动作、表情与脚本。JSON 路径相对于场景文件解析。.fescene 包含引用媒体、原始 .puppet 与可选 .petscript.json，可移到其他电脑。导入会检查路径、符号链接、版本与解压上限。FrontEngine 场景保持为场景包；.puppet 保持为单一 Imervue 角色。

macOS：可选 macos extra 以 macOS 13+ 与公开 PyObjC framework 为基准。后端提供 ScreenCaptureKit 屏幕／窗口捕获与系统音频、麦克风捕获、Quartz 窗口几何、Accessibility 窗口布局与移动、CoreMIDI、媒体键及 F12 退出。屏幕录制、辅助功能与麦克风权限分别检查；请到系统设置 → 隐私与安全性，依提示重新启动。其他程序窗口的透明度／强制置顶、Space 指定，以及让其他程序捕获时排除覆盖层仍不可用。本 Windows 开发环境尚未验证 macOS 原生授权、硬件与性能。 Settings → macOS 权限与能力会逐项列出可用、不可用或不支持，并显示权限或安装原因。

插件：启用加载不代表授权插件。plugin.json 或单文件 sidecar 声明版本、身份、入口与能力；Python import 前检查同意，授权绑定内容摘要。程序或声明改变就需重新同意；旧插件需明确完全信任。Settings → Revoke plugin grants 可撤销保存的授权；已在运行的程序需重新启动才能卸载。Python 插件仍具有完整应用程序权限，声明与同意不是操作系统沙箱。

渲染：Settings → Overlay rendering 可选 Auto、GPU 或 Software，并查看实际后端。GPU 合成器以 OpenGL texture、shader 与 framebuffer 处理图层顺序、变换、不透明度与裁剪；初始化失败时回退软件并显示原因。已有 QPainter 内容仍可能先由 CPU 转成光栅图再上传；web／video／原生 widget 可能使用独立窗口。捕获与录制可能将 GPU 画面读回 CPU，这不代表零拷贝捕获或已测得性能提升。 场景 GPU 合成目前涵盖 IMAGE、GIF 与 TEXT；puppet 使用自己的 Imervue 窗口绘制。

Windows OCR 的 WinRT 投影包包含于 FrontEngine 的一般 Windows 安装；请安装需要的 Windows 识别语言。Tesseract 的可执行文件与训练语言数据需单独安装。可选 puppet extra 会安装 Imervue>=1.0.90；macos extra 安装 macOS 13+ 的公开 PyObjC framework。请使用下列命令。docs/formats/ 提供 puppet、pet.json、petscript 与场景示例。

.. code-block:: console

    pip install "frontengine[puppet]"
    pip install "frontengine[macos]"
