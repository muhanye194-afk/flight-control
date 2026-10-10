# Feed Cache Key Migration Incident Runbook

## Scope

当 Feed 服务在缓存 Key 格式、命名空间或兼容逻辑发布后出现错误率上升、延迟升高时，使用本手册。

## Confirming signals

- Feed 错误率明显升高。
- 缓存命中率低于正常基线，或接近 0。
- 数据库延迟、超时或连接压力随着缓存未命中一起升高。
- Redis 命令队列或 CPU 压力升高。
- 最近发布涉及 cache key、namespace、序列化或兼容逻辑。
- Trace 显示请求先发生 cache miss，随后出现数据库超时。

## Investigation sequence

1. 对比发布前后的缓存命中率、错误率和 P95 延迟。
2. 检查新旧 Cache Key 是否可以兼容读取。
3. 确认缓存 Key 的 namespace、版本号和序列化格式是否发生变化。
4. 将异常开始时间与最近发布记录关联。
5. 区分根因与连锁症状：数据库超时可能是缓存未命中风暴的后果。

## Root-cause indicators

- Cache Key 迁移后，旧缓存无法被新版本读取。
- 新 namespace 导致大规模缓存未命中。
- 回源数据库请求突然增加，并与命中率下降同步发生。
- 最近变更直接修改了缓存 Key 或兼容逻辑。

## Safe remediation

- 不自动修改生产缓存配置或清空缓存。
- 需要人工审批后，才可回滚 Cache Key 迁移或恢复兼容读取逻辑。
- 先在小流量环境验证新旧 Key 兼容性。
- 对回滚或修复操作设置监控和停止条件。

## Verification

- Feed 错误率恢复到 2% 以下。
- Feed P95 延迟恢复到 800ms 以下。
- 缓存命中率恢复到 85% 以上。
- Redis 队列压力下降，数据库超时停止增长。