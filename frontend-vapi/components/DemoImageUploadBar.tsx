"use client";

import { useCallback, useRef, useState } from "react";

import { IMAGE_UPLOAD_TOKEN } from "@/lib/types";

const DEMO_SESSION_ID = "jake-demo";

async function compressImageForUpload(file: File): Promise<File> {
  const bitmap = await createImageBitmap(file);
  const maxEdge = 1200;
  const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height));
  const width = Math.max(1, Math.round(bitmap.width * scale));
  const height = Math.max(1, Math.round(bitmap.height * scale));

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return file;
  }
  ctx.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob(resolve, "image/jpeg", 0.82);
  });
  if (!blob) {
    return file;
  }

  const baseName = file.name.replace(/\.[^.]+$/, "") || "damage";
  return new File([blob], `${baseName}.jpg`, { type: "image/jpeg" });
}

type DemoImageUploadBarProps = {
  visible: boolean;
  onSent?: () => void;
};

export default function DemoImageUploadBar({
  visible,
  onSent,
}: DemoImageUploadBarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChoosePhoto = () => {
    setError(null);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please choose a JPEG, PNG, or WebP image.");
      return;
    }

    try {
      const compressed = await compressImageForUpload(file);
      if (imagePreview) {
        URL.revokeObjectURL(imagePreview);
      }
      setImageFile(compressed);
      setImagePreview(URL.createObjectURL(compressed));
      setError(null);
    } catch {
      setError("Could not read that image. Try another photo.");
    }
  };

  const sendImage = useCallback(async () => {
    if (!imageFile || sending) return;

    setSending(true);
    setError(null);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const result = e.target?.result;
          if (typeof result === "string") {
            resolve(result);
          } else {
            reject(new Error("Failed to read image"));
          }
        };
        reader.onerror = () => reject(new Error("Failed to read image"));
        reader.readAsDataURL(imageFile);
      });

      const res = await fetch("/api/respond", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: DEMO_SESSION_ID,
          transcript: IMAGE_UPLOAD_TOKEN,
          conversation_history: [],
          context: { awaiting_image: true },
          images: [
            {
              id: crypto.randomUUID(),
              url: dataUrl,
              mime_type: imageFile.type || "image/jpeg",
              uploaded_at: Date.now(),
            },
          ],
        }),
      });

      const payload = (await res.json()) as { error?: string };
      if (!res.ok) {
        throw new Error(payload.error ?? `Upload failed (${res.status})`);
      }

      setSent(true);
      onSent?.();
      window.setTimeout(() => setSent(false), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send photo");
    } finally {
      setSending(false);
    }
  }, [imageFile, sending, onSent]);

  if (!visible && !sent) {
    return null;
  }

  if (sent) {
    return (
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100,
          background: "rgba(0,0,0,0.92)",
          borderBottom: "2px solid rgba(95,212,160,0.5)",
          padding: "14px 16px",
          textAlign: "center",
          color: "#5fd4a0",
          fontWeight: 600,
          fontSize: 15,
        }}
      >
        ✓ Photo sent — agent is reviewing damage
      </div>
    );
  }

  if (!visible) {
    return null;
  }

  return (
    <>
      <style jsx global>{`
        @keyframes demo-upload-bar-in {
          from {
            opacity: 0;
            transform: translateY(-100%);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .demo-upload-bar {
          animation: demo-upload-bar-in 350ms ease forwards;
        }
        .demo-upload-file-input {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }
      `}</style>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/*"
        onChange={(e) => void handleFileChange(e)}
        className="demo-upload-file-input"
      />

      <div
        className="demo-upload-bar"
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100,
          background:
            "linear-gradient(180deg, rgba(255,107,74,0.28) 0%, rgba(12,8,8,0.98) 100%)",
          borderBottom: "3px solid #ff6b4a",
          boxShadow: "0 10px 40px rgba(255,107,74,0.35)",
          padding: "16px",
        }}
      >
        <p
          style={{
            margin: "0 0 14px",
            fontSize: 16,
            fontWeight: 700,
            color: "#ff6b4a",
            textAlign: "center",
          }}
        >
          📸 UPLOAD DAMAGE PHOTO
        </p>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            maxWidth: 520,
            margin: "0 auto",
          }}
        >
          <button
            type="button"
            onClick={handleChoosePhoto}
            style={{
              flex: "1 1 0",
              minHeight: 56,
              background: "#ffffff",
              color: "#111111",
              border: "none",
              borderRadius: 12,
              fontSize: 17,
              fontWeight: 800,
              letterSpacing: "0.08em",
              cursor: "pointer",
              boxShadow: "0 4px 16px rgba(0,0,0,0.35)",
            }}
          >
            UPLOAD
          </button>

          {imagePreview ? (
            <img
              src={imagePreview}
              alt="Selected"
              style={{
                width: 56,
                height: 56,
                flexShrink: 0,
                objectFit: "cover",
                borderRadius: 10,
                border: "3px solid #ff6b4a",
              }}
            />
          ) : (
            <div
              style={{
                width: 56,
                height: 56,
                flexShrink: 0,
                borderRadius: 10,
                border: "2px dashed rgba(255,255,255,0.25)",
              }}
            />
          )}

          <button
            type="button"
            onClick={() => void sendImage()}
            disabled={!imageFile || sending}
            style={{
              flex: "1 1 0",
              minHeight: 56,
              background: imageFile ? "#ff6b4a" : "rgba(255,107,74,0.3)",
              color: imageFile ? "#ffffff" : "rgba(255,255,255,0.4)",
              border: "none",
              borderRadius: 12,
              fontSize: 17,
              fontWeight: 800,
              letterSpacing: "0.08em",
              cursor: imageFile && !sending ? "pointer" : "not-allowed",
              boxShadow: imageFile ? "0 4px 16px rgba(255,107,74,0.45)" : "none",
              opacity: sending ? 0.7 : 1,
            }}
          >
            {sending ? "…" : "SEND"}
          </button>
        </div>

        <p
          style={{
            margin: "10px 0 0",
            textAlign: "center",
            fontSize: 12,
            color: error ? "#ff6b6b" : "rgba(255,255,255,0.5)",
          }}
        >
          {error ?? "Tap UPLOAD → pick photo → tap SEND"}
        </p>
      </div>
    </>
  );
}
