const APPID = "d4a08fc6e76e47a290815339fa2dd125";
const CHANNEL = "test";
const TOKEN = "007eJxTYNBpTu/719s1+7BZO6P23pul0bOtjz06U5+Rf7uk56n81VMKDCkmiQYWaclmqeZmqSbmiUaWBhaGpsbGlmmJRikphkam//fHpDQEMjK87EpjYmSAQBCfhaEktbiEgQEA8GMiHg==";
let UID;

  // Инициализируйте клиента Agora
const client = AgoraRTC.createClient({mode: 'rtc', codec: 'vp8'});

let localTracks = []
let remoteUsers ={}

document.addEventListener("DOMContentLoaded", function() {
    let joinAndDisplayLocalStream = async ()=>{
        UID = await client.join(APPID, CHANNEL, TOKEN, null)
        localTracks = await AgoraRTC.createMicrophoneAndCameraTracks()

        let player =  `<div class="video-container" id="video-container-${UID}">
        <div class="username-wrapper"><span class="user-name">My Name</span></div>
        <div class="video-player" id="user-${UID}"></div>
      </div>`
      document.getElementById('video-streams').insertAdjacentHTML('beforeend', player)

      localTracks[1].play(`user-${UID}`)

      await client.publish([localTracks[0], localTracks[1]])
    }
    joinAndDisplayLocalStream()
});
