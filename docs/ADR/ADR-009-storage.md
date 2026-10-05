# ADR-009: Artifact Storage

## Status
Accepted

## Context
CareerOS generates resume PDFs, DOCX files, browser screenshots, and other artifacts that must be stored and served securely.

## Decision
Abstract storage via StorageBackend interface. Local filesystem for development. S3-compatible object storage for production.

## Backends
- LocalStorage: ./storage directory, served via API endpoint
- S3Storage: any S3-compatible service (AWS S3, MinIO, Cloudflare R2)

## Security
- Files never exposed publicly
- All access mediated through authenticated API endpoints
- Filenames are UUIDs — no path traversal risk
- S3 bucket is private; no public-read ACL

## Consequences
- STORAGE_BACKEND=local for dev, s3 for prod
- boto3 handles S3 operations
- Local storage not suitable for multi-instance production deployments
