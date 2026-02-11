# 本地安装openclaw微信公众号助手

## 1 安装openclaw

执行命令：

```shell
curl -fsSL https://openclaw.ai/install.sh | bash
```

安装完毕自动执行openclaw onboard，模型必须选择MiniMax，所需的key需要Minimax Coding Plan 版本（获取地址：https://platform.minimaxi.com/subscribe/coding-plan ），如图，其它都选默认项，暂时不配置channel和skill，后面配置。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/03da061b-4211-443c-8cad-c9cf12099d75.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/531656d9-7679-44a7-9c3d-e54c25ccd53d.png)

```shell
sk-cp-okxxxxx
```

## 2 更新模型key配置

本地启动后，需要在配置文件里更新模型的key，操作如图，需要手动更新models.providers.minimax.baseUrl和增加models.providers.minimax.apiKey。然后点右上方save。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/b5f4f5ef-9908-4ee8-a8e0-f5c2d3e174d4.png)

```shell
"models": {
    "providers": {
      "minimax": {
        "baseUrl": "https://api.minimaxi.com/anthropic",
        "apiKey": "sk-cp-xxxx"
```

此时chat聊天它会正常应答：![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/3cc55b10-2777-4c26-8989-5809dcb2a6d4.png)

## 3 安装skill文件

把本项目解压后，内容复制到~/.openclaw目录下，结果如图：


![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/d6707ad8-eba0-4f6a-9b2c-79c22748dbfc.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/6729372c-71a2-4b1f-825e-9f1703cf0609.png)


编辑配置文件，更新所需的配置值：
配置文件路径： 
```shell
~/.openclaw/skills/Wechat-Artical/scripts/config.json 
```

IMAGE_API_BASE_URL=生成图模型的baseUrl

IMAGE_API_KEY=生成图模型的key

IMAGE_MODEL_NAME=生成图模型名称，默认值gemini-3-pro-image-preview

IMAGE_FALLBACK_MODEL_NAME=生成图备用模型名称，默认值gemini-2.0-flash-exp-image-generation

WECHAT_APPID=要发布的微信公众号的appId

WECHAT_APPSECRET=要发布的微信公众号secret

WECHAT_AUTHOR=要发布的微信公众号名称


## 4 通知openclaw安装这个skill

本地openclaw gateway通过Chat聊天，输入如下内容让它安装这个skill，它会自动安装所需依赖。

```shell
帮我安装skill到本地，所需文件都在~/.openclaw/skills目录下
```

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/464e5901-b7f2-4586-bbbb-076dffb04cc5.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/efd1a610-e67a-4746-aa9e-0f371e9bced8.png)

然后就可以通过Chat让它写公众号了。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/f86a8c0d-f4e8-44df-a89a-fa9fb925de51.png)


## 5 安装飞书插件

openclaw 默认不内置飞书 Channel，需要额外安装插件，社区已经有小伙伴实现并开源 项目地址： [https://github.com/m1heng/clawdbot-feishu](https://github.com/m1heng/clawdbot-feishu) 


#### 创建飞书机器人

1、进入飞书应用中心  
飞书开放平台：[https://open.feishu.cn/app?lang=zh-CN](https://open.feishu.cn/app?lang=zh-CN)

2、新建企业自建应用

路径： 创建应用 → 企业自建应用；基础信息按提示填写即可（名称、描述等），完成创建后进入应用详情页。

路径： 应用能力 → 添加应用能力；添加机器人，完成后点击上方的 创建版本。

#### 配置飞书机器人应用权限

路径：权限管理 → 批量导入权限；直接把下面的 json 复制进入，导入权限后点击申请开通。

```json
{
    "scopes": {
      "tenant": [
        "im:message",
        "im:message:send_as_bot",
        "im:message.p2p_msg:readonly",
        "im:message.group_at_msg:readonly",
        "im:resource",
        "im:message.group_msg",
        "im:message:readonly",
        "im:message:update",
        "im:message:recall",
        "im:message.reactions:read"
      ],
      "user": [
        "contact:user.base:readonly"
      ]
    }
  }
```

#### 获取飞书机器人调用密钥

路径：凭证与基础信息 → 应用凭证 ，将机器人的 App ID / App Secret 保存下来等下有用。

#### openclaw 安装飞书插件

```shell
openclaw plugins install @m1heng-clawd/feishu
```

#### openclaw 更新配置

```plaintext
# appId、appSecret 需要在 飞书应用后台获取，填入你自己的
openclaw config set channels.feishu.appId "cli_xxxxx" 
openclaw config set channels.feishu.appSecret "your_app_secret" 
openclaw config set channels.feishu.enabled true 
openclaw config set channels.feishu.connectionMode "websocket"
```

#### openclaw 重启

```plaintext
openclaw gateway restart
```

#### 设置飞书机器人 Callback

一定要完成上面的步骤，最后完成这一步，要不然会提示 “应用未建立长连接”。  
路径：事件与回调 → 回调配置 → 定阅方式；使用长连接接受回调，然后点击保存。  
路径：事件与回调 → 事件配置 → 定阅方式；使用长连接接受回调，然后点击保存。  
路径：事件与回调 → 添加事件；然后选择 消息与群组 里面的 接收消息（im.message.receive\_v1），缺了这一步，你给机器人发消息会没有回复。  
完成后，点击上面的创建版本，发布。

现在，你就可以跟飞书机器人私聊，或者把他拉到某个群聊 @它了。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/4EZlweZ8e13BZqxA/img/02d43872-0347-4715-b369-306bd79613c0.png)
