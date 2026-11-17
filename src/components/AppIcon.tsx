import i32 from "../assets/app-icon-32.png";
import i64 from "../assets/app-icon-64.png";
import i128 from "../assets/app-icon-128.png";
import i256 from "../assets/app-icon-256.png";
import i512 from "../assets/app-icon-512.png";

export function AppIcon({ size = 32 }: { size?: number }) {
  return (
    <img
      className="app-icon"
      width={size}
      height={size}
      sizes={`${size}px`}
      src={i128}
      srcSet={`${i32} 32w, ${i64} 64w, ${i128} 128w, ${i256} 256w, ${i512} 512w`}
      alt="File Converter"
      draggable={false}
    />
  );
}
