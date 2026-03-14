# ai-manus 商业化改造 TODO

## Phase 1: Fork + 环境搭建
- [x] Fork ai-manus 到 xie38388/ai-manus
- [x] 克隆到本地，设置 upstream remote

## Phase 2: SOVR gate_check（核心差异化）
- [x] 后端：创建 sovr/ 模块（policy.py + audit.py + gate.py）
- [x] 后端：在 BaseAgent.execute() 的工具调用前插入 gate_check
- [x] 后端：高风险操作（delete_file, shell_exec, external_api）需审批
- [x] 后端：低风险操作（read_file, search）自动放行
- [x] 后端：SHA-256 审计链记录所有操作
- [x] 后端：SOVR API 路由（/sovr/stats, /sovr/trust-score）
- [x] 测试：19/19 通过

## Phase 3: Stripe 订阅 + Credit 系统
- [x] 后端：billing/ 模块（products.py + credit_service.py + stripe_service.py）
- [x] 后端：billing_routes.py（checkout, webhook, balance, usage, portal）
- [x] 后端：3 档定价（Free $0 / Pro $19.9 / Team $49.9）
- [x] 后端：Credit 系统（扣减、充值、每日限额、月度重置）
- [x] 后端：agent_task_runner.py 注入 credit 检查
- [x] 测试：17/17 通过

## Phase 4: 前端 Billing + Credit 显示
- [x] 前端：billing.ts API 客户端（getTiers, getBalance, createCheckout, createPortal）
- [x] 前端：useBilling.ts composable（全局 credit 状态管理 + 30s 缓存）
- [x] 前端：PricingPage.vue（3 档定价卡片 + credit 消耗说明）
- [x] 前端：CreditBadge.vue（侧边栏底部余额 + 进度条 + 低余额警告）
- [x] 前端：UpgradeDialog.vue（credits 不足时升级提示弹窗）
- [x] 前端：路由注册 /pricing（在 MainLayout 下）
- [x] 前端：LeftPanel.vue 集成 CreditBadge
- [x] Landing Page — 用户确认不需要，保持原有提问框首页

## Phase 5: 用量仪表盘 + 多租户隔离
- [x] 前端：UsagePage.vue（credit 余额、今日用量、Agent 次数、本月用量、趋势预测、SOVR 信任分）
- [x] 前端：路由注册 /usage
- [x] 后端：按 tier 限速/限功能（已在 credit_service.py 中实现 daily_agent_limit + credits_monthly）

## Phase 6: 测试 + 部署
- [ ] 语法验证所有新文件
- [ ] 推送到 GitHub
- [ ] 更新 memory 文件
