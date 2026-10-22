from onelogin.saml2.auth import OneLogin_Saml2_Auth


class SAMLAdapter:
    """
    SAML SSO secure adapter boundary.
    Provides the structural components for SAML login, ACS response processing,
    and metadata validation.
    """

    def __init__(self, entity_id: str, sso_url: str, x509_cert: str):
        self.entity_id = entity_id
        self.sso_url = sso_url
        self.x509_cert = x509_cert

        self.settings = {
            "strict": True,
            "debug": True,
            "sp": {
                "entityId": "https://gossipmesh.example.com/metadata",
                "assertionConsumerService": {
                    "url": "https://gossipmesh.example.com/acs",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": "https://gossipmesh.example.com/sls",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
            },
            "idp": {
                "entityId": self.entity_id,
                "singleSignOnService": {
                    "url": self.sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "singleLogoutService": {
                    "url": self.sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self.x509_cert,
            },
        }

    def _get_dummy_req(self, saml_response: str = None) -> dict:
        req = {
            "https": "on",
            "http_host": "localhost",
            "server_port": "443",
            "script_name": "/acs",
            "get_data": {},
            "post_data": {},
        }
        if saml_response:
            req["post_data"]["SAMLResponse"] = saml_response
        return req

    def build_authn_request(self) -> str:
        """
        Generates a SAML AuthnRequest.
        Returns the Redirect URL (SSO URL + encoded SAMLRequest).
        """
        auth = OneLogin_Saml2_Auth(self._get_dummy_req(), self.settings)
        return auth.login()

    def parse_response(self, saml_response: str) -> dict:
        """
        Parses and validates the SAML response payload.
        """
        auth = OneLogin_Saml2_Auth(self._get_dummy_req(saml_response), self.settings)
        auth.process_response()

        errors = auth.get_errors()
        if errors:
            raise ValueError(f"SAML Validation Error: {errors}")

        return auth.get_attributes()

    def validate_certificate(self) -> bool:
        """
        Validates that the stored X509 certificate is well-formed.
        """
        if not self.x509_cert or "BEGIN CERTIFICATE" not in self.x509_cert:
            return False
        return True

    def process_logout(self) -> str:
        """
        Generates a SAML LogoutRequest.
        """
        auth = OneLogin_Saml2_Auth(self._get_dummy_req(), self.settings)
        return auth.logout()
