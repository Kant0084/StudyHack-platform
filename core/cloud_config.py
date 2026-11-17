"""云服务公开配置（来自 activate 返回的 publicConfig）。

这些值是公开的（endpoint 为应用域名，publishableKey 仅标识应用、不含权限），
可安全放入前端源码。请勿放入日志。
"""

# 应用数据平面地址（cloud-service activate 返回）
ENDPOINT = "https://studyhack.app.workbuddy.host"

# 标识应用、无权限的公开密钥（server 通过 Origin 精确匹配校验）
PUBLISHABLE_KEY = "wbpk_Ag4nfCICa2Ke03foZRaebl_381iqP1t403omKSmNlkkPiCtG09I2k7f"

# OAuth Relay 基地址（web 端登录用，LLM/数据库调用可不需要）
OAUTH_RELAY_BASE_URL = "https://www.workbuddy.cn/v2/as/genie-baas/oauth"
