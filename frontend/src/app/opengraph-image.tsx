import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "DataPulse - Turn Raw Sales Data into Revenue Intelligence";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #0D1117 0%, #161B22 50%, #0D1117 100%)",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        {/* Accent glow */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "600px",
            height: "600px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(0,191,165,0.15) 0%, transparent 70%)",
          }}
        />

        {/* Logo */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            marginBottom: "24px",
          }}
        >
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "rgba(0,191,165,0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#D97706",
              fontSize: "28px",
              fontWeight: "bold",
            }}
          >
            D
          </div>
          <span
            style={{
              fontSize: "36px",
              fontWeight: "bold",
              color: "#D97706",
            }}
          >
            DataPulse
          </span>
        </div>

        {/* Headline */}
        <h1
          style={{
            fontSize: "48px",
            fontWeight: "bold",
            color: "#E6EDF3",
            textAlign: "center",
            maxWidth: "800px",
            lineHeight: 1.2,
            margin: 0,
          }}
        >
          Turn Raw Sales Data into Revenue Intelligence
        </h1>

        {/* Subtitle */}
        <p
          style={{
            fontSize: "20px",
            color: "#A8B3BD",
            textAlign: "center",
            maxWidth: "600px",
            marginTop: "16px",
          }}
        >
          Automated medallion pipeline with AI-powered insights
        </p>

        {/* Tech badges */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            marginTop: "32px",
          }}
        >
          {["Polars", "dbt", "FastAPI", "Next.js"].map((badge) => (
            <span
              key={badge}
              style={{
                padding: "6px 16px",
                borderRadius: "20px",
                border: "1px solid #30363D",
                color: "#A8B3BD",
                fontSize: "14px",
              }}
            >
              {badge}
            </span>
          ))}
        </div>
      </div>
    ),
    { ...size }
  );
}
