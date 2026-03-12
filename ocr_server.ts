import { PaddleOcrService } from "ppu-paddle-ocr";

// --- Configuration ---
const PORT = parseInt(process.env.OCR_PORT || "18765", 10);
const MODEL_BASE_URL =
  "https://media.githubusercontent.com/media/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/main";
const DICT_BASE_URL =
  "https://raw.githubusercontent.com/PT-Perkasa-Pilar-Utama/ppu-paddle-ocr-models/main";

// --- Logger ---
const logger = {
  info: (message: string) => console.log(`[OCR Server] ${message}`),
  error: (message: string) => console.error(`[OCR Server] ${message}`),
};

// --- Service Initialization ---
let service: PaddleOcrService;

try {
  logger.info("Initializing PaddleOCR service...");
  service = new PaddleOcrService({
    model: {
      detection: `${MODEL_BASE_URL}/detection/PP-OCRv5_mobile_det_infer.onnx`,
      recognition: `${MODEL_BASE_URL}/recognition/PP-OCRv5_mobile_rec_infer.onnx`,
      charactersDictionary: `${DICT_BASE_URL}/recognition/ppocrv5_dict.txt`,
    },
  });
  await service.initialize();
  logger.info("✅ PaddleOCR service ready.");
} catch (err: any) {
  logger.error(`❌ Failed to initialize PaddleOCR service: ${err.message}`);
  process.exit(1);
}

// --- Graceful Shutdown ---
const shutdown = async () => {
  logger.info("Shutting down gracefully...");
  await service.destroy();
  process.exit(0);
};

// --- Server ---
const server = Bun.serve({
  port: PORT,
  async fetch(req) {
    const url = new URL(req.url);
    logger.info(`Received request: ${req.method} ${url.pathname}`);

    if (url.pathname === "/health" && req.method === "GET") {
      return new Response(JSON.stringify({ status: "ok" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

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
        logger.error(`OCR recognition failed: ${err.message}`);
        return new Response(
          JSON.stringify({ status: "error", message: err.message }),
          { status: 500, headers: { "Content-Type": "application/json" } }
        );
      }
    }

    if (url.pathname === "/shutdown" && req.method === "POST") {
      setTimeout(shutdown, 50); // Respond before exiting
      return new Response(JSON.stringify({ status: "shutting_down" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("Not Found", { status: 404 });
  },
  error(err) {
    logger.error(`Server error: ${err.message}`);
    return new Response("Internal Server Error", { status: 500 });
  },
});

logger.info(`🚀 Listening on http://localhost:${server.port}`);

// Handle OS signals
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
