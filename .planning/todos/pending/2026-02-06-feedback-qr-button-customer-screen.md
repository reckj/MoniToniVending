---
created: 2026-02-06T21:10
title: Add feedback QR code button to customer screen
area: ui
files:
  - monitoni/ui/customer_screen.py
---

## Problem

Customer screen has no way for users to give feedback or suggest product wishes. Want a button at the bottom of the customer screen that displays a QR code linking to a Google Form for collecting feedback and product requests.

## Solution

- Add a small button at the bottom of the customer screen (aligned with existing UI style)
- On tap, show a QR code (generated or static image) linking to a configurable Google Form URL
- URL should be configurable via config (e.g., `system.feedback_form_url`)
- QR display could reuse the existing QR preview pattern from QRManagementScreen
- Button should be unobtrusive — doesn't interfere with main purchase flow
