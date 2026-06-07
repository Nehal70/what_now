import { DataPacket_Kind, RoomServiceClient } from "livekit-server-sdk";

export type AgentTurnNotifyPayload = {
  type: "turn_complete";
  transcript: string;
  response: string;
  context: Record<string, unknown>;
};

export async function notifyAgentSpeak(
  roomName: string | null,
  payload: AgentTurnNotifyPayload,
): Promise<void> {
  if (!roomName) {
    return;
  }

  const url = process.env.LIVEKIT_URL;
  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;

  if (!url || !apiKey || !apiSecret) {
    console.warn("LiveKit credentials missing — agent will not speak image response");
    return;
  }

  const host = url.replace(/^wss:\/\//, "https://").replace(/^ws:\/\//, "http://");
  const roomService = new RoomServiceClient(host, apiKey, apiSecret);
  const data = new TextEncoder().encode(JSON.stringify(payload));

  await roomService.sendData(roomName, data, DataPacket_Kind.RELIABLE);
}
