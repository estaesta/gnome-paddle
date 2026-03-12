import { PaddleOcrService } from "ppu-paddle-ocr";

const MODEL_BASE_URL =
  "https://media.githubusercontent.com/media/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/main";
const DICT_BASE_URL =
  "https://raw.githubusercontent.com/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/main";

const service = new PaddleOcrService({
  model: {
    detection: `${MODEL_BASE_URL}/detection/PP-OCRv5_mobile_det_infer.onnx`,
    recognition: `${MODEL_BASE_URL}/recognition/PP-OCRv5_mobile_rec_infer.onnx`,
    charactersDictionary: `${DICT_BASE_URL}/recognition/ppocrv5_dict.txt`,
  },
});

console.log("[OCR Server] Initializing PaddleOCR (downloading models on first run)...");
await service.initialize();
console.log("[OCR Server] PaddleOCR ready!");

const server = Bun.serve({
  port: 18765,
  async fetch(req) {
    const url = new URL(req.url);

    // Health check
    if (url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // OCR endpoint: accepts image as raw body
    if (url.pathname === "/ocr" && req.method === "POST") {
      try {
        const imageBuffer = await req.arrayBuffer();
        const result = await service.recognize(imageBuffer);

        return new Response(
          JSON.stringify({
            status: "success",
            text: result.text,
            lines: result.lines ?? [],
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      } catch (err: any) {
        return new Response(
          JSON.stringify({ status: "error", message: err.message }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      }
    }

    // Shutdown endpoint
    if (url.pathname === "/shutdown" && req.method === "POST") {
      // Graceful shutdown
      setTimeout(async () => {
        await service.destroy();
        process.exit(0);
      }, 100);
      return new Response(JSON.stringify({ status: "shutting_down" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("Not Found", { status: 404 });
  },
});

console.log(`[OCR Server] Listening on http://localhost:${server.port}`);

// Handle graceful shutdown on signals
process.on("SIGTERM", async () => {
  console.log("[OCR Server] Received SIGTERM, shutting down...");
  await service.destroy();
  process.exit(0);
});

process.on("SIGINT", async () => {
  console.log("[OCR Server] Received SIGINT, shutting down...");
  await service.destroy();
  process.exit(0);
});
