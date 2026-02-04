from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
from .logger import logger
from .services.agent.controller import AgentController
from .services.recognize.controller import ASRController



app = FastAPI(title="Lina AI Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/agent")
async def agent_websocket(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket agent connected")
    
    agent = AgentController(ws)

    try:
        while True:
            try:
                message = await ws.receive()
                if message.get("text") is not None:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    if msg_type == "user_text":
                        logger.info(f"user_text: {data}")
                        await agent.handle_text(data.get("prompt", ""))

                    elif msg_type == "reset":
                        agent.reset()

                    else:
                        await ws.send_json({
                            "type": "error",
                            "message": f"Unknown message type for agent: {msg_type}"
                        })

            except WebSocketDisconnect:
                logger.info("WebSocket agent disconnected")
                await agent.cleanup()
                break  

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                await ws.send_json({
                    "type": "error",
                    "message": f"Invalid JSON: {str(e)}"
                })

            except Exception as e:
                logger.exception(f"Error processing agent message: {e}")
                await ws.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except Exception as e:
        logger.exception("Fatal server error in agent WebSocket handler")
        await agent.cleanup()


@app.websocket("/ws/recognition")
async def recognition_websocket(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket recognition connected")
    
    asr = ASRController(ws)

    try:
        while True:
            try:
                message = await ws.receive()

                if message.get("bytes") is not None:
                    await asr.handle_audio_chunk(message["bytes"])
                    continue

                if message.get("text") is not None:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")

                    if msg_type == "recognize_start":
                        logger.info("Handle recognize start")
                        await asr.handle_recognize_start(data)

                    elif msg_type == "recognize_final":
                        logger.info("Handle recognize final")
                        await asr.handle_recognize_end()

                    else:
                        await ws.send_json({
                            "type": "error",
                            "message": f"Unknown message type for recognition: {msg_type}"
                        })

            except WebSocketDisconnect:
                logger.info("WebSocket recognition disconnected")
                break  

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                await ws.send_json({
                    "type": "error",
                    "message": f"Invalid JSON: {str(e)}"
                })

            except Exception as e:
                logger.exception(f"Error processing recognition message: {e}")
                await ws.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except Exception as e:
        logger.exception("Fatal server error in recognition WebSocket handler")
        await asr.cleanup()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Lina Agent Server",
        "endpoints": {
            "agent_ws": "/ws/agent",
            "recognition_ws": "/ws/recognition"
        }
    }