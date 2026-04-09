"""NDA and Rules of Engagement legal text — versioned for audit trail."""

NDA_VERSION = "1.0"
ROE_VERSION = "1.0"

NDA_TEXT = """
NON-DISCLOSURE AGREEMENT AND RULES OF ENGAGEMENT
AutoPentest AI — Automated Penetration Testing Platform

Version: 1.0
Effective Date: Upon electronic acceptance

═══════════════════════════════════════════════════════════════
SECTION 1 — PARTIES
═══════════════════════════════════════════════════════════════

This Non-Disclosure Agreement ("Agreement") is entered into by and between:

(a) AutoPentest AI B.V. ("Service Provider"), a company registered under
    the laws of the Netherlands; and

(b) The individual or entity accepting this Agreement electronically
    ("Client"), as identified by their authenticated user account.

Collectively referred to as the "Parties."

═══════════════════════════════════════════════════════════════
SECTION 2 — PURPOSE
═══════════════════════════════════════════════════════════════

The Client engages the Service Provider to perform automated security
testing ("Penetration Testing") against the Client's own digital
infrastructure ("Target Systems") as defined in the scope section of
the scan configuration.

═══════════════════════════════════════════════════════════════
SECTION 3 — AUTHORIZATION AND OWNERSHIP
═══════════════════════════════════════════════════════════════

3.1 The Client hereby represents and warrants that:

    (a) The Client is the legal owner of, or has explicit written
        authorization from the owner to conduct security testing on,
        all Target Systems specified in the scan scope;

    (b) The Client has obtained all necessary internal approvals,
        including but not limited to approval from IT management,
        legal department, and executive leadership;

    (c) All third-party hosting providers, cloud service providers,
        and ISPs have been notified of the testing as required by
        their terms of service;

    (d) The Client assumes full legal responsibility for the
        authorization of this testing.

3.2 The Client acknowledges that unauthorized access to computer
    systems is a criminal offense under applicable law, including
    but not limited to:
    - EU Directive 2013/40/EU on attacks against information systems
    - The Computer Fraud and Abuse Act (CFAA) — 18 U.S.C. § 1030
    - The Computer Misuse Act 1990 (UK)
    - Wetboek van Strafrecht (Netherlands) Article 138ab

═══════════════════════════════════════════════════════════════
SECTION 4 — SCOPE OF TESTING
═══════════════════════════════════════════════════════════════

4.1 Testing shall be limited exclusively to the Target Systems
    specified in the scan configuration, including:
    - Domain names
    - IP addresses and ranges
    - Specific ports (if restricted)
    - URL paths (if restricted)

4.2 The Service Provider's automated tools are technically restricted
    to only communicate with verified Target Systems. Network-level
    controls prevent any out-of-scope testing.

4.3 The following activities are EXCLUDED from all testing:
    - Denial of Service (DoS/DDoS) attacks
    - Physical security testing
    - Social engineering of personnel
    - Testing of systems not explicitly in scope
    - Data exfiltration of actual customer/user data
    - Modification or deletion of production data
    - Installation of persistent backdoors or malware

═══════════════════════════════════════════════════════════════
SECTION 5 — RULES OF ENGAGEMENT
═══════════════════════════════════════════════════════════════

5.1 TESTING METHODOLOGY
    The Service Provider employs industry-standard automated security
    testing tools operating within the following parameters:
    - Reconnaissance: passive and active information gathering
    - Vulnerability scanning: automated CVE and misconfiguration detection
    - Web application testing: OWASP Top 10 vulnerability assessment
    - Network testing: service enumeration and known vulnerability checks
    - Authentication testing: default credential and weak password detection
    - SSL/TLS analysis: cryptographic configuration assessment
    - Cloud security: public exposure and misconfiguration detection
    - OSINT: publicly available information gathering

5.2 SAFE TESTING PRACTICES
    (a) All testing uses non-destructive techniques only
    (b) Brute force attempts are rate-limited and use only common
        credential lists (no exhaustive attacks)
    (c) SQL injection and command injection tests use safe payloads
    (d) No actual exploitation of discovered vulnerabilities
    (e) Testing automatically stops if system instability is detected

5.3 TIMING
    Testing may be initiated at the Client's discretion. The Client
    accepts responsibility for scheduling tests during appropriate
    maintenance windows if system availability is a concern.

═══════════════════════════════════════════════════════════════
SECTION 6 — CONFIDENTIALITY
═══════════════════════════════════════════════════════════════

6.1 Both Parties agree to maintain strict confidentiality regarding:
    (a) All scan results, findings, and vulnerabilities discovered
    (b) The Client's system architecture and configuration details
    (c) Any business information incidentally observed during testing

6.2 DATA HANDLING — PRIVACY BY DEFAULT
    (a) Raw scan output is processed in-memory only and automatically
        discarded after AI analysis unless the Client explicitly
        enables report storage.
    (b) If report storage is enabled, data is encrypted at rest
        using AES-256-GCM and accessible only to the Client.
    (c) Temporary scan data in Redis is automatically deleted
        after 1 hour (TTL-based expiry).
    (d) The Service Provider does not retain, sell, share, or
        analyze Client scan data for any purpose other than
        providing the requested service.

6.3 This confidentiality obligation survives termination of this
    Agreement for a period of five (5) years.

═══════════════════════════════════════════════════════════════
SECTION 7 — LIABILITY
═══════════════════════════════════════════════════════════════

7.1 The Service Provider exercises reasonable care in performing
    automated security testing. However, the Client acknowledges that:
    (a) Penetration testing inherently carries risk of service disruption
    (b) Automated tools may generate network traffic that triggers
        security alerts or intrusion detection systems
    (c) No security assessment can guarantee the discovery of all
        vulnerabilities

7.2 The Service Provider's total liability under this Agreement
    shall not exceed the fees paid by the Client for the specific
    scan in question.

7.3 The Client shall indemnify and hold harmless the Service Provider
    against any claims, damages, or expenses arising from:
    (a) Testing conducted on systems the Client was not authorized to test
    (b) Inaccurate scope definitions provided by the Client
    (c) Actions taken by the Client based on scan results

═══════════════════════════════════════════════════════════════
SECTION 8 — DATA PROTECTION (GDPR COMPLIANCE)
═══════════════════════════════════════════════════════════════

8.1 The Service Provider processes personal data in accordance with
    the EU General Data Protection Regulation (GDPR) 2016/679.

8.2 Personal data collected is limited to:
    (a) User account information (email, name, company)
    (b) NDA acceptance records (IP address, timestamp, user agent)
    (c) Billing information (processed by Stripe; not stored by us)

8.3 The legal basis for processing is:
    (a) Contract performance (Article 6(1)(b) GDPR) for the service
    (b) Legitimate interest (Article 6(1)(f) GDPR) for security logging
    (c) Legal obligation (Article 6(1)(c) GDPR) for audit records

═══════════════════════════════════════════════════════════════
SECTION 9 — TERMINATION
═══════════════════════════════════════════════════════════════

9.1 Either Party may terminate this Agreement at any time by
    providing written notice.

9.2 Upon termination, the Client may request deletion of all
    stored report data. The Service Provider will comply within
    30 days, except for audit records required by law.

═══════════════════════════════════════════════════════════════
SECTION 10 — GOVERNING LAW
═══════════════════════════════════════════════════════════════

10.1 This Agreement shall be governed by and construed in accordance
     with the laws of the Netherlands.

10.2 Any disputes arising from this Agreement shall be submitted to
     the competent courts of Amsterdam, the Netherlands.

═══════════════════════════════════════════════════════════════
SECTION 11 — ELECTRONIC ACCEPTANCE
═══════════════════════════════════════════════════════════════

By checking the acceptance checkboxes and proceeding with the scan,
the Client:

(a) Acknowledges having read and understood this Agreement in full
(b) Confirms authorization to test the specified Target Systems
(c) Agrees to be bound by the terms and conditions herein
(d) Understands that this electronic acceptance constitutes a
    legally binding agreement equivalent to a physical signature

The acceptance is recorded with:
- Timestamp (UTC)
- Client IP address
- Authenticated user identifier
- SHA-256 hash of this document version

This record is maintained as an immutable audit trail.

═══════════════════════════════════════════════════════════════
END OF AGREEMENT
═══════════════════════════════════════════════════════════════
""".strip()
