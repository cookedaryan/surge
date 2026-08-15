package com.power.surge.controller;

import com.power.surge.dto.admin.CreateUserRequest;
import com.power.surge.dto.admin.ResetPasswordRequest;
import com.power.surge.dto.admin.UpdateUserRequest;
import com.power.surge.dto.admin.UserSummaryResponse;
import com.power.surge.service.UserAdminService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

/**
 * Account administration.
 *
 * <p>The class-level {@code @PreAuthorize} covers every method, so a route added later is
 * restricted by default rather than by remembering to annotate it.
 */
@RestController
@RequestMapping("/api/v1/admin/users")
@PreAuthorize("hasRole('ADMIN')")
public class UserAdminController {

    private final UserAdminService userAdminService;

    public UserAdminController(UserAdminService userAdminService) {
        this.userAdminService = userAdminService;
    }

    @GetMapping
    public ResponseEntity<List<UserSummaryResponse>> listUsers() {
        return ResponseEntity.ok(userAdminService.listUsers());
    }

    @PostMapping
    public ResponseEntity<UserSummaryResponse> createUser(
            @Valid @RequestBody CreateUserRequest request,
            Authentication authentication
    ) {
        UserSummaryResponse created = userAdminService.createUser(request, authentication.getName());
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    /** Partial update: role, suspension state, or both. */
    @PatchMapping("/{userId}")
    public ResponseEntity<UserSummaryResponse> updateUser(
            @PathVariable UUID userId,
            @Valid @RequestBody UpdateUserRequest request,
            Authentication authentication
    ) {
        return ResponseEntity.ok(userAdminService.updateUser(userId, request, authentication.getName()));
    }

    /** Separate from the partial update so the reset is audited as its own distinct event. */
    @PostMapping("/{userId}/password")
    public ResponseEntity<Void> resetPassword(
            @PathVariable UUID userId,
            @Valid @RequestBody ResetPasswordRequest request,
            Authentication authentication
    ) {
        userAdminService.resetPassword(userId, request, authentication.getName());
        return ResponseEntity.noContent().build();
    }
}
