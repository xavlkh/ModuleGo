# ModuleGo Copilot Review Instructions

When reviewing a pull request:

- Keep changes simple, readable, and suitable for a student project.
- Review only the files changed by the pull request. Do not suggest unrelated rewrites.
- Check for correctness, security issues, missing validation, and missing tests.
- Never expose Supabase or Gemini secret keys in frontend code or committed files.
- Keep Supabase access behind the Flask backend.
- Follow PEP 8 and require docstrings for Flask view functions.
- Follow the existing Vanilla JavaScript and JSDoc conventions.
- Confirm that relevant automated tests pass before recommending a merge.
- Explain each suggestion in clear, concise language.
