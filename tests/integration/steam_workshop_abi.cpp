// Read-only ABI probe, compiled against the user's selected Steamworks SDK.
#include <cstdio>
#include <cstddef>
#include "steam_api.h"

int main() {
    std::printf("{\"CallbackMessage\":[%zu,%zu,%zu],"
                "\"CallCompleted\":[%zu,%zu,%zu],"
                "\"CreateResult\":[%zu,%zu,%zu],"
                "\"SubmitResult\":[%zu,%zu,%zu],"
                "\"ItemDetails\":[%zu,%zu,%zu],"
                "\"DetailsResult\":[%zu,%zu,%zu]}\n",
        sizeof(CallbackMsg_t), offsetof(CallbackMsg_t, m_pubParam), offsetof(CallbackMsg_t, m_cubParam),
        sizeof(SteamAPICallCompleted_t), offsetof(SteamAPICallCompleted_t, m_iCallback),
        offsetof(SteamAPICallCompleted_t, m_cubParam),
        sizeof(CreateItemResult_t), offsetof(CreateItemResult_t, m_nPublishedFileId),
        offsetof(CreateItemResult_t, m_bUserNeedsToAcceptWorkshopLegalAgreement),
        sizeof(SubmitItemUpdateResult_t), offsetof(SubmitItemUpdateResult_t, m_bUserNeedsToAcceptWorkshopLegalAgreement),
        offsetof(SubmitItemUpdateResult_t, m_nPublishedFileId),
        sizeof(SteamUGCDetails_t), offsetof(SteamUGCDetails_t, m_ulSteamIDOwner),
        offsetof(SteamUGCDetails_t, m_nConsumerAppID),
        sizeof(SteamUGCRequestUGCDetailsResult_t), offsetof(SteamUGCRequestUGCDetailsResult_t, m_details),
        offsetof(SteamUGCRequestUGCDetailsResult_t, m_bCachedData));
    return 0;
}
