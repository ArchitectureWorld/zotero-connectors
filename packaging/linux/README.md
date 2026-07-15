# Linux 双 Zotero 实例安装

本安装方式只面向当前用户，并固定使用以下映射：

```text
ZZH Chrome 9222 → ZZH Connector → Zotero 23119
NSY Chrome 9223 → NSY Connector → Zotero 23120
```

## 前置条件

- 两个 Chrome 实例分别使用调试端口 `9222` 和 `9223`；
- 两个 Zotero 实例分别监听 `127.0.0.1:23119` 和 `127.0.0.1:23120`。

## 安装包直接安装

解压后，在安装包根目录运行：

```bash
./install.sh
```

稳定扩展 ID、两个 Native Host 名称、两个 Zotero 地址和两个 Unix Socket 路径均已内置，不需要填写 Chrome Profile 路径。

安装器会把 Connector 复制到稳定目录：

```text
~/.local/lib/zotero-script-trigger/browser-extension
```

从源码目录安装时运行：

```bash
python3 packaging/linux/install-linux-dual-instance.py
```

`--extension-id`、`--zzh-profile-dir` 和 `--nsy-profile-dir` 仅保留为高级覆盖参数，不是正常安装所需参数。两个 Profile 路径如需记录，必须同时提供且不能相同。

## 在 Chrome 中加载 Connector

Chrome 不允许普通脚本静默安装“解压扩展”，因此两个独立 Profile 都需要进行一次手动加载：

1. 分别在 ZZH 和 NSY Chrome 中打开 `chrome://extensions`；
2. 开启右上角“开发者模式”；
3. 点击“加载已解压的扩展程序”；
4. 两个 Profile 都选择：

```text
~/.local/lib/zotero-script-trigger/browser-extension
```

5. 确认扩展 ID 为：

```text
anakemdifclhajhpbjlgfpeokaphddam
```

6. 再分别打开安装器输出的 ZZH、NSY `settings_pages`，点击“应用并重载 Connector”。

安装器**不会**修改 Chrome 的 `Preferences`、`Local State` 或扩展 LevelDB。

## 安装内容

安装器会生成：

- 一份稳定目录中的 Connector；
- 两个 Native Messaging Manifest；
- 两份独立配置和认证密钥；
- 两个独立 Unix Socket 路径；
- 两个 Native Host 启动器；
- 一个共享 CLI：`~/.local/bin/zotero-script-trigger`；
- 两个扩展设置页地址。

## 自检

```bash
~/.local/bin/zotero-script-trigger --instance ZZH ping
~/.local/bin/zotero-script-trigger --instance NSY ping
```

返回值应分别包含：

```text
ZZH / 23119 / org.zotero.script_trigger.zzh
NSY / 23120 / org.zotero.script_trigger.nsy
```

## 卸载

安装包根目录：

```bash
./uninstall.sh
```

源码目录：

```bash
python3 packaging/linux/uninstall-linux-dual-instance.py
```

卸载器只移除安装器管理的文件；同目录中的用户文件不会被删除。
