# BUCT Media HUB OpenAPI 文档

本目录存放后端接口的 OpenAPI 导出文件，可直接导入 ApiFox、Apifox CLI、Postman 等工具。

## 文件说明

- `openapi.json`：推荐导入文件，兼容性最好。
- `openapi.yaml`：便于人工阅读和版本对比。

## 导出方式

在项目根目录执行：

```powershell
python scripts/export_openapi.py
```

脚本会基于 `backend/app/main.py` 中注册的 FastAPI 应用重新生成规范文件。

## 鉴权说明

- 前端业务登录：`POST /api/v1/auth/login`
- OpenAPI / OAuth2 password flow 登录：`POST /api/v1/auth/token`
- 受保护接口统一使用：`Authorization: Bearer <access_token>`

其中图片访问接口还支持通过查询参数传 token：

```text
?access_token=<access_token>
```

这是为了兼容浏览器在 `<img>` 请求里无法稳定附带 `Authorization` 头的场景。

## 导入 ApiFox

1. 新建项目或进入现有项目。
2. 选择“导入数据” -> “OpenAPI/Swagger”。
3. 导入 `docs/openapi/openapi.json`。
4. 为环境变量设置服务地址，例如 `http://localhost:8000`。
5. 登录后把返回的 `access_token` 配置为 Bearer Token。
