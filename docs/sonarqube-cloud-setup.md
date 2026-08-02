# SonarQube Cloud Setup

The repository files are ready for CI-based SonarQube Cloud analysis. A
repository owner must complete the one-time account setup below.

## One-time GitHub setup

1. Sign in to SonarQube Cloud with the GitHub account that owns `ModuleGo`.
2. Install the SonarQube Cloud GitHub App and allow access to `ModuleGo`.
3. Import the repository as a SonarQube Cloud project.
4. Select **With GitHub Actions** as the analysis method. Disable automatic
   analysis so that the pytest coverage report can be imported.
5. In the SonarQube Cloud project tutorial, generate the analysis token.
6. Add it in GitHub under **Settings > Secrets and variables > Actions** as a
   repository secret named `SONAR_TOKEN`.
7. Confirm that the generated project key and organization key match
   `xavlkh_ModuleGo` and `xavlkh` in `sonar-project.properties`. Update those
   two values if SonarQube Cloud generated different keys.

## Verification

Run the CI workflow or open a pull request. The Python 3.12 job should:

1. Run pytest and create `coverage.xml`.
2. Upload the code and coverage results to SonarQube Cloud.
3. Add a SonarQube Quality Gate check to the pull request.

Until `SONAR_TOKEN` is added, CI prints a skip message instead of failing.
