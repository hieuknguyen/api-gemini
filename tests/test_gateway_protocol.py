import unittest

from gateway_protocol import format_upstream_error, response_inner


class GatewayErrorFormattingTests(unittest.TestCase):
    def test_formats_google_error_with_status_and_message(self):
        message = format_upstream_error(
            403,
            '{"error":{"code":403,"status":"PERMISSION_DENIED",'
            '"message":"Cloud Code Private API is not enabled for this project."}}',
        )

        self.assertIn("HTTP 403 PERMISSION_DENIED", message)
        self.assertIn("Cloud Code Private API is not enabled", message)

    def test_redacts_credentials_and_does_not_dump_raw_body(self):
        message = format_upstream_error(
            401,
            '{"error":{"message":"Bearer secret-token access_token=abc123 '
            'refresh_token=xyz789"}}',
        )

        self.assertIn("Bearer [REDACTED]", message)
        self.assertIn("access_token=[REDACTED]", message)
        self.assertIn("refresh_token=[REDACTED]", message)
        self.assertNotIn("secret-token", message)
        self.assertNotIn("abc123", message)
        self.assertNotIn("xyz789", message)

    def test_includes_error_code_from_success_envelope(self):
        with self.assertRaisesRegex(Exception, r"PERMISSION_DENIED: Cloud Code Private API"):
            response_inner({
                "error": {
                    "status": "PERMISSION_DENIED",
                    "message": "Cloud Code Private API is not enabled.",
                }
            })


if __name__ == "__main__":
    unittest.main()
