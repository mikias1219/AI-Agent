export default function Avatar({ name = 'A', size = 'size-9' }) {
  return (
    <span
      className={`${size} inline-grid shrink-0 place-items-center rounded-full bg-brand-100 text-sm font-semibold text-brand-400`}
    >
      {name.charAt(0).toUpperCase()}
    </span>
  );
}
