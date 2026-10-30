export default function Avatar({ name = 'M', size = 'size-9' }) {
  return (
    <span
      className={`${size} inline-grid shrink-0 place-items-center rounded-full bg-[#f4e5da] text-sm font-semibold text-[#9a7155]`}
    >
      {name.charAt(0).toUpperCase()}
    </span>
  );
}
