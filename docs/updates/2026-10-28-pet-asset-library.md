# Installed assets and restart restoration

PetAssetLibrary copies only a layered manifest and its declared PNG resources
into pet-assets under the application's startup directory. Package directories
use hashes of exact ID/version pairs, avoiding platform-dependent asset-name
paths. Existing versions are preserved. Staging is validated before directory
rename; failed installations leave no partial package. The library bounds entries,
file bytes and decoded image pixels, and reports malformed installed packages.

Desktop pets resolve their saved character and clothing references at startup.
Unavailable or corrupt resources preserve the saved appearance and set
appearance_error; restore_appearance retries after repair. A successfully restored
renderer uses the same publication path as live wardrobe application. Profile
exports continue to contain references rather than copied artwork.

Tests exposed a Windows handle leak on invalid images: the exception traceback
retained a QImageReader and its open file while staging cleanup ran. The decoder
now explicitly closes its device in finally, including validation failures.

72 related tests passed after the correction: asset installation, wardrobe,
profile sessions, customization, layered pixels, drops and typing settlement.
New tests verify independent installed copies, rejection of duplicate versions,
cleanup of failed installs, reporting of damaged packages, reopening a saved
outfit and retry after resource repair. Tests use offscreen Qt and temporary
libraries, not the user's production pet-assets directory.

Installation, missing-resource feedback and retry still need to be exposed in
the wardrobe UI. Official character/clothing animation assets and native desktop
acceptance remain unfinished; the full implementation goal stays active.
