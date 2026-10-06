import Image, { StaticImageData } from "next/image";

// Full-cover photo for a positioned parent; the optimizer serves a sized,
// compressed version and a blur placeholder while it loads.
export default function Photo({
  src, alt = "", position = "center", priority = false, sizes = "100vw",
}: { src: StaticImageData; alt?: string; position?: string; priority?: boolean; sizes?: string }) {
  return (
    <Image
      src={src} alt={alt} fill priority={priority} sizes={sizes} placeholder="blur" quality={80}
      className="photo-img" style={{ objectFit: "cover", objectPosition: position }}
    />
  );
}
