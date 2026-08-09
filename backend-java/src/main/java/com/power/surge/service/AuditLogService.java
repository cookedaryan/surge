package com.power.surge.service;

import com.power.surge.domain.AuditLog;
import com.power.surge.repository.AuditLogRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@Transactional(readOnly = true)
public class AuditLogService {

    private final AuditLogRepository auditLogRepository;

    public AuditLogService(AuditLogRepository auditLogRepository) {
        this.auditLogRepository = auditLogRepository;
    }

    @Transactional
    public AuditLog recordAudit(String username, String action, String resourceType, String resourceId, String details) {
        AuditLog log = new AuditLog(username, action, resourceType, resourceId, details);
        return auditLogRepository.save(log);
    }

    public List<AuditLog> getRecentAuditLogs() {
        return auditLogRepository.findTop50ByOrderByTimestampDesc();
    }
}
