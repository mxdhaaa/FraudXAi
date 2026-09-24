# API Integrations

## IP-API (IP Geolocation & Threat Intelligence)

* **Purpose**: Resolves an IP address to geographical location, ISP, and ASN information to detect impossible travel and high-risk origin countries.
* **Official Documentation**: [https://ip-api.com/docs/api:json](https://ip-api.com/docs/api:json)
* **Endpoint**: `http://ip-api.com/json/{query}`
* **Authentication Method**: None required for the free tier.
* **Environment Variables**: None required.
* **Request Format**: GET request with the IP address as `{query}`.
* **Response Format**: JSON object with fields like `country`, `city`, `isp`, `org`, `lat`, `lon`.
* **Rate Limits**: 45 requests per minute.
* **Fallback Behaviour**: If rate limited or unavailable, the system defaults to "Location intelligence unavailable" and relies on core ML scoring based on transaction velocity and amounts.
