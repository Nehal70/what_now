"use client";

import { useEffect, useRef, useState } from "react";

type StagedImage = {
  id: string;
  previewUrl: string;
};

type ImageUploadPanelProps = {
  sessionId: string;
  isLive: boolean;
};

export default function ImageUploadPanel({
  sessionId,
  isLive,
}: ImageUploadPanelProps) {
  const [staged, setStaged] = useState<StagedImage[]>([]);
  const [prompt, setPrompt] = useState<string | null>(null);
  const [awaitingImage, setAwaitingImage] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isLive) {
      return;
    }

    const source = new EventSource(`/api/sessions/${sessionId}/events`);

    source.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as {
          type?: string;
          data?: { prompt?: string };
        };

        if (parsed.type === "ping") return;

        if (parsed.type === "image_requested") {
          setAwaitingImage(true);
          setPrompt(parsed.data?.prompt ?? "Upload photos in the app");
          setSent(false);
        }
      } catch {
        // ignore malformed events
      }
    };

    return () => {
      source.close();
    };
  }, [isLive, sessionId]);

  if (!isLive) {
    return null;
  }

  const visible = awaitingImage || staged.length > 0;

  if (!visible && !sent) {
    return null;
  }

  async function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) {
      return;
    }

    setError(null);
    setUploading(true);

    try {
      const remaining = 3 - staged.length;
      const files = Array.from(fileList).slice(0, remaining);

      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(`/api/sessions/${sessionId}/images`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const data = (await res.json()) as { error?: string };
          throw new Error(data.error ?? "Upload failed");
        }

        const data = (await res.json()) as {
          id: string;
          preview_url: string;
        };

        setStaged((prev) => [
          ...prev,
          { id: data.id, previewUrl: data.preview_url },
        ]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  async function handleSend() {
    if (staged.length === 0 || sending) {
      return;
    }

    setError(null);
    setSending(true);

    try {
      const res = await fetch(`/api/sessions/${sessionId}/images/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_ids: staged.map((image) => image.id) }),
      });

      if (!res.ok) {
        const data = (await res.json()) as { error?: string };
        throw new Error(data.error ?? "Send failed");
      }

      setStaged([]);
      setAwaitingImage(false);
      setPrompt(null);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="image-upload-panel">
      {sent ? (
        <p className="image-upload-sent">Photos sent — the agent is reviewing them.</p>
      ) : null}

      {awaitingImage && prompt ? (
        <p className="image-upload-prompt">{prompt}</p>
      ) : null}

      {staged.length > 0 ? (
        <div className="image-upload-previews">
          {staged.map((image) => (
            <img
              key={image.id}
              src={image.previewUrl}
              alt="Selected upload"
              className="image-upload-thumb"
            />
          ))}
        </div>
      ) : null}

      {awaitingImage || staged.length > 0 ? (
        <div className="image-upload-actions">
          <input
            ref={inputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            multiple
            className="image-upload-input"
            disabled={uploading || staged.length >= 3}
            onChange={(e) => void handleFiles(e.target.files)}
          />
          <button
            type="button"
            className="image-upload-add"
            disabled={uploading || staged.length >= 3}
            onClick={() => inputRef.current?.click()}
          >
            {uploading ? "Uploading…" : staged.length >= 3 ? "Max 3 photos" : "Add photo"}
          </button>
          <button
            type="button"
            className="image-upload-send"
            disabled={staged.length === 0 || sending}
            onClick={() => void handleSend()}
          >
            {sending ? "Sending…" : `Send ${staged.length || ""} photo${staged.length === 1 ? "" : "s"}`.trim()}
          </button>
        </div>
      ) : null}

      {error ? <p className="image-upload-error">{error}</p> : null}
    </div>
  );
}
