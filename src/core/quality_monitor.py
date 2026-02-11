"""
质量监控和告警系统
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from .quality import MetadataQualityScore, QualityIssue, QualityMetrics, QualityLevel
from .quality_assessor import QualityAssessor


class AlertChannel(str, Enum):
    """告警渠道"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    LOG = "log"


class AlertRule:
    """告警规则"""
    
    def __init__(self,
                 name: str,
                 condition: Callable[[MetadataQualityScore], bool],
                 channels: List[AlertChannel],
                 severity: str = "medium",
                 enabled: bool = True,
                 description: str = ""):
        """
        初始化告警规则
        
        Args:
            name: 规则名称
            condition: 条件函数，返回 True 表示触发告警
            channels: 告警渠道列表
            severity: 严重程度
            enabled: 是否启用
            description: 规则描述
        """
        self.name = name
        self.condition = condition
        self.channels = channels
        self.severity = severity
        self.enabled = enabled
        self.description = description
    
    def should_alert(self, score: MetadataQualityScore) -> bool:
        """判断是否应该告警"""
        if not self.enabled:
            return False
        try:
            return self.condition(score)
        except Exception as e:
            print(f"评估告警规则 {self.name} 失败: {e}")
            return False


class QualityMonitor:
    """质量监控器"""
    
    def __init__(self, assessor: QualityAssessor):
        """
        初始化质量监控器
        
        Args:
            assessor: 质量评估器
        """
        self.assessor = assessor
        self.alert_rules: List[AlertRule] = []
        self.alert_history: List[Dict[str, Any]] = []
        
        # 告警配置
        self.email_config: Optional[Dict[str, Any]] = None
        self.webhook_config: Optional[Dict[str, Any]] = None
        self.websocket_callbacks: List[Callable] = []
        
        # 加载默认告警规则
        self._load_default_alert_rules()
    
    def _load_default_alert_rules(self):
        """加载默认告警规则"""
        # 综合评分过低告警
        self.add_alert_rule(AlertRule(
            name="low_overall_score",
            condition=lambda s: s.overall_score < 0.5,
            channels=[AlertChannel.LOG],
            severity="high",
            description="综合质量评分低于 0.5"
        ))
        
        # 严重质量问题告警
        self.add_alert_rule(AlertRule(
            name="critical_quality",
            condition=lambda s: s.get_quality_level() == QualityLevel.CRITICAL,
            channels=[AlertChannel.LOG],
            severity="critical",
            description="质量等级为严重"
        ))
        
        # 完整性过低告警
        self.add_alert_rule(AlertRule(
            name="low_completeness",
            condition=lambda s: s.completeness_score < 0.6,
            channels=[AlertChannel.LOG],
            severity="medium",
            description="完整性评分低于 0.6"
        ))
        
        # 数据过期告警
        self.add_alert_rule(AlertRule(
            name="stale_data",
            condition=lambda s: s.freshness_score < 0.3,
            channels=[AlertChannel.LOG],
            severity="medium",
            description="数据新鲜度评分低于 0.3"
        ))
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.alert_rules.append(rule)
    
    def remove_alert_rule(self, rule_name: str):
        """移除告警规则"""
        self.alert_rules = [r for r in self.alert_rules if r.name != rule_name]
    
    def configure_email(self, smtp_host: str, smtp_port: int, 
                       username: str, password: str,
                       from_email: str, to_emails: List[str]):
        """
        配置邮件告警
        
        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 端口
            username: 用户名
            password: 密码
            from_email: 发件人邮箱
            to_emails: 收件人邮箱列表
        """
        self.email_config = {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_email": from_email,
            "to_emails": to_emails
        }
    
    def configure_webhook(self, url: str, method: str = "POST", 
                         headers: Optional[Dict[str, str]] = None):
        """
        配置 Webhook 告警
        
        Args:
            url: Webhook URL
            method: HTTP 方法
            headers: HTTP 头
        """
        self.webhook_config = {
            "url": url,
            "method": method,
            "headers": headers or {}
        }
    
    def register_websocket_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        注册 WebSocket 回调
        
        Args:
            callback: 回调函数
        """
        self.websocket_callbacks.append(callback)
    
    def monitor_entity(self, entity_id: str, score: MetadataQualityScore) -> List[Dict[str, Any]]:
        """
        监控单个实体，检查是否需要告警
        
        Args:
            entity_id: 实体ID
            score: 质量评分
            
        Returns:
            触发的告警列表
        """
        alerts = []
        
        for rule in self.alert_rules:
            if rule.should_alert(score):
                alert = {
                    "entity_id": entity_id,
                    "rule_name": rule.name,
                    "severity": rule.severity,
                    "score": score.to_dict(),
                    "timestamp": datetime.now().isoformat(),
                    "channels": [ch.value for ch in rule.channels]
                }
                
                # 发送告警
                self._send_alert(alert, rule.channels)
                
                alerts.append(alert)
                self.alert_history.append(alert)
        
        return alerts
    
    def _send_alert(self, alert: Dict[str, Any], channels: List[AlertChannel]):
        """发送告警"""
        for channel in channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email_alert(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook_alert(alert)
                elif channel == AlertChannel.WEBSOCKET:
                    self._send_websocket_alert(alert)
                elif channel == AlertChannel.LOG:
                    self._send_log_alert(alert)
            except Exception as e:
                print(f"发送告警到 {channel.value} 失败: {e}")
    
    def _send_email_alert(self, alert: Dict[str, Any]):
        """发送邮件告警"""
        if not self.email_config:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config["from_email"]
            msg['To'] = ", ".join(self.email_config["to_emails"])
            msg['Subject'] = f"元数据质量告警: {alert['rule_name']} - {alert['severity']}"
            
            body = f"""
            元数据质量告警
            
            实体ID: {alert['entity_id']}
            规则名称: {alert['rule_name']}
            严重程度: {alert['severity']}
            综合评分: {alert['score']['overall_score']:.2f}
            质量等级: {alert['score']['quality_level']}
            时间: {alert['timestamp']}
            
            详细信息:
            {json.dumps(alert['score'], indent=2, ensure_ascii=False)}
            """
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            server = smtplib.SMTP(self.email_config["smtp_host"], self.email_config["smtp_port"])
            server.starttls()
            server.login(self.email_config["username"], self.email_config["password"])
            server.send_message(msg)
            server.quit()
        except Exception as e:
            print(f"发送邮件告警失败: {e}")
    
    def _send_webhook_alert(self, alert: Dict[str, Any]):
        """发送 Webhook 告警"""
        if not self.webhook_config:
            return
        
        try:
            url = self.webhook_config["url"]
            method = self.webhook_config.get("method", "POST")
            headers = self.webhook_config.get("headers", {})
            
            if method.upper() == "POST":
                response = requests.post(url, json=alert, headers=headers, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=alert, headers=headers, timeout=10)
            else:
                print(f"不支持的 HTTP 方法: {method}")
                return
            
            response.raise_for_status()
        except Exception as e:
            print(f"发送 Webhook 告警失败: {e}")
    
    def _send_websocket_alert(self, alert: Dict[str, Any]):
        """发送 WebSocket 告警"""
        for callback in self.websocket_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"WebSocket 回调执行失败: {e}")
    
    def _send_log_alert(self, alert: Dict[str, Any]):
        """发送日志告警"""
        print(f"[质量告警] {alert['severity'].upper()}: {alert['rule_name']} - 实体 {alert['entity_id']} - 评分 {alert['score']['overall_score']:.2f}")
    
    def get_alert_history(self, 
                         entity_id: Optional[str] = None,
                         rule_name: Optional[str] = None,
                         severity: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取告警历史
        
        Args:
            entity_id: 实体ID过滤
            rule_name: 规则名称过滤
            severity: 严重程度过滤
            limit: 限制数量
            
        Returns:
            告警历史列表
        """
        filtered = self.alert_history
        
        if entity_id:
            filtered = [a for a in filtered if a.get("entity_id") == entity_id]
        if rule_name:
            filtered = [a for a in filtered if a.get("rule_name") == rule_name]
        if severity:
            filtered = [a for a in filtered if a.get("severity") == severity]
        
        # 按时间倒序排序
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return filtered[:limit]
    
    def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取告警统计
        
        Args:
            days: 统计天数
            
        Returns:
            告警统计信息
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        recent_alerts = [
            a for a in self.alert_history
            if datetime.fromisoformat(a.get("timestamp", "2000-01-01")) >= cutoff_time
        ]
        
        # 按严重程度统计
        severity_counts = {}
        rule_counts = {}
        
        for alert in recent_alerts:
            severity = alert.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            rule_name = alert.get("rule_name", "unknown")
            rule_counts[rule_name] = rule_counts.get(rule_name, 0) + 1
        
        return {
            "total_alerts": len(recent_alerts),
            "severity_distribution": severity_counts,
            "rule_distribution": rule_counts,
            "period_days": days
        }
    
    def monitor_batch(self, scores: List[MetadataQualityScore]) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量监控实体
        
        Args:
            scores: 质量评分列表
            
        Returns:
            告警结果字典，key 为实体ID，value 为告警列表
        """
        results = {}
        for score in scores:
            alerts = self.monitor_entity(score.entity_id, score)
            if alerts:
                results[score.entity_id] = alerts
        return results


class QualityTrendAnalyzer:
    """质量趋势分析器"""
    
    def __init__(self):
        """初始化趋势分析器"""
        self.score_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def record_score(self, entity_id: str, score: MetadataQualityScore):
        """
        记录质量评分
        
        Args:
            entity_id: 实体ID
            score: 质量评分
        """
        if entity_id not in self.score_history:
            self.score_history[entity_id] = []
        
        self.score_history[entity_id].append({
            "timestamp": score.assessed_at.isoformat(),
            "overall_score": score.overall_score,
            "completeness_score": score.completeness_score,
            "accuracy_score": score.accuracy_score,
            "consistency_score": score.consistency_score,
            "freshness_score": score.freshness_score
        })
    
    def get_trend(self, entity_id: str, days: int = 30) -> Dict[str, Any]:
        """
        获取质量趋势
        
        Args:
            entity_id: 实体ID
            days: 统计天数
            
        Returns:
            趋势数据
        """
        if entity_id not in self.score_history:
            return {"entity_id": entity_id, "trend": "no_data"}
        
        cutoff_time = datetime.now() - timedelta(days=days)
        history = [
            h for h in self.score_history[entity_id]
            if datetime.fromisoformat(h["timestamp"]) >= cutoff_time
        ]
        
        if not history:
            return {"entity_id": entity_id, "trend": "no_data"}
        
        # 计算趋势
        scores = [h["overall_score"] for h in history]
        if len(scores) >= 2:
            trend = "improving" if scores[-1] > scores[0] else "degrading" if scores[-1] < scores[0] else "stable"
            change_rate = (scores[-1] - scores[0]) / scores[0] if scores[0] > 0 else 0
        else:
            trend = "stable"
            change_rate = 0
        
        return {
            "entity_id": entity_id,
            "trend": trend,
            "change_rate": change_rate,
            "current_score": scores[-1],
            "initial_score": scores[0],
            "data_points": len(history),
            "history": history
        }
    
    def get_aggregate_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        获取聚合质量趋势
        
        Args:
            days: 统计天数
            
        Returns:
            聚合趋势数据
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        
        # 收集所有实体的历史数据
        all_scores = []
        for entity_id, history in self.score_history.items():
            for h in history:
                if datetime.fromisoformat(h["timestamp"]) >= cutoff_time:
                    all_scores.append({
                        "timestamp": h["timestamp"],
                        "overall_score": h["overall_score"]
                    })
        
        if not all_scores:
            return {"trend": "no_data"}
        
        # 按时间分组计算平均值
        daily_scores = {}
        for score in all_scores:
            date = datetime.fromisoformat(score["timestamp"]).date().isoformat()
            if date not in daily_scores:
                daily_scores[date] = []
            daily_scores[date].append(score["overall_score"])
        
        daily_averages = {
            date: sum(scores) / len(scores)
            for date, scores in daily_scores.items()
        }
        
        dates = sorted(daily_averages.keys())
        if len(dates) >= 2:
            trend = "improving" if daily_averages[dates[-1]] > daily_averages[dates[0]] else "degrading" if daily_averages[dates[-1]] < daily_averages[dates[0]] else "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "daily_averages": daily_averages,
            "current_average": daily_averages[dates[-1]] if dates else 0,
            "initial_average": daily_averages[dates[0]] if dates else 0
        }



