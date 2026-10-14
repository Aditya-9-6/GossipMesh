1. **Update Models**:
   - In `gossipmesh/models/organization.py`:
     - Add `is_suspended` column to `UserOrganization`.
     - Add `OrganizationInvitation` model with `email`, `token`, `organization_id`, `role`.
   - Create `gossipmesh/models/project.py`:
     - Add `Project` model with `id`, `organization_id`, `name`, `description`.
   - Update `gossipmesh/models/__init__.py` to re-export `Project` and `OrganizationInvitation`.
2. **Update API router for Organizations (`gossipmesh/api/routers/organizations.py`)**:
   - `POST /` - create organization (also adds current user as 'admin').
   - `POST /{org_id}/invitations` - create an invitation (requires 'admin' role).
   - `POST /invitations/{token}/accept` - accept invitation (find by token, add current user to org).
   - `PATCH /{org_id}/members/{user_id}/role` - assign role (requires 'admin').
   - `POST /{org_id}/projects` - create project (requires 'admin').
   - `POST /{org_id}/repositories` - connect repository (requires 'admin').
   - `DELETE /{org_id}/members/{user_id}` - remove member (requires 'admin').
   - `PATCH /{org_id}/members/{user_id}/suspend` - suspend member (requires 'admin').
   - Add comprehensive Pydantic schemas (e.g., `OrganizationCreate`, `InvitationCreate`, `ProjectCreate`, `RepositoryConnect`).
   - Add dependency for authorization (`require_org_admin(org_id)`).
   - Insert `AuditEvent` records for every modifying action.
3. **Write Unit Tests**:
   - Create `tests/api/routers/test_organizations.py` to cover all endpoints.
   - Use `mock_db_session` and `test_client`.
4. **Complete pre commit steps**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
