package com.power.surge.service;

import com.power.surge.domain.AuditLog;
import com.power.surge.repository.AuditLogRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@Transactional(readOnly = true)
public class AuditLogService {

    private static final Logger log = LoggerFactory.getLogger(AuditLogService.class);

    private final AuditLogRepository auditLogRepository;

    public AuditLogService(AuditLogRepository auditLogRepository) {
        this.auditLogRepository = auditLogRepository;
    }

    @Transactional
    public AuditLog recordAudit(String username, String action, String resourceType, String resourceId, String details) {
        AuditLog entry = new AuditLog(username, action, resourceType, resourceId, details);
        return auditLogRepository.save(entry);
    }

    /**
     * Records an action against whoever is making the current request.
     *
     * <p>Resolving the actor here rather than threading a username through every service keeps
     * instrumentation to a single line at each call site, which is the difference between the log
     * covering the application and covering only the two places somebody remembered to plumb.
     *
     * <p>Runs in its own transaction so the record survives even when the surrounding work is
     * rolled back — a failed import or a rejected job is precisely the kind of thing worth having
     * in the log. For the same reason a logging failure must never break the operation being
     * logged, so exceptions are swallowed and reported to the application log instead.
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void record(String action, String resourceType, String resourceId, String details) {
        try {
            auditLogRepository.save(new AuditLog(currentUsername(), action, resourceType, resourceId, details));
        } catch (RuntimeException e) {
            log.warn("Failed to write audit entry {} for {} {}: {}", action, resourceType, resourceId, e.toString());
        }
    }

    /**
     * The authenticated principal, or {@code "anonymous"}. Every audited route requires a token, so
     * the fallback should only ever appear for a scheduled or internal caller.
     */
    private String currentUsername() {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication == null || !authentication.isAuthenticated()) {
            return "anonymous";
        }
        String name = authentication.getName();
        return name != null && !name.isBlank() ? name : "anonymous";
    }

    public List<AuditLog> getRecentAuditLogs() {
        return auditLogRepository.findTop50ByOrderByTimestampDesc();
    }
}
