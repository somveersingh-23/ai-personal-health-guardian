# Member 3 Android module

This isolated Compose app owns only Member 3 surfaces: assistant, insights,
alerts, caregivers, and the emergency workflow. It talks to the standalone
Member 3 FastAPI app at `http://10.0.2.2:8000` for emulator development.

## Run

1. Start the API from the repository root:
   `uvicorn app.api.member3.app:app --app-dir backend --reload`
2. Open this directory in Android Studio, install API 36 when prompted, and run
   the `app` configuration on an emulator.
3. For a physical device or production build, replace
   `MEMBER3_API_BASE_URL` with an HTTPS endpoint. Cleartext access is limited to
   the emulator loopback host.

The temporary `demo-user` identity must be replaced by the shared authenticated
user provider when the team's auth layer is merged. No emergency call or
caregiver notification is performed without a backend workflow and explicit
confirmation.
