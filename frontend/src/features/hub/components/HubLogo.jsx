export default function HubLogo({ className = 'h-8 w-8' }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#4f46e5" />
      <path
        d="M8 22V10h4.2l3.3 8.2L18.8 10H23v12h-2.6v-7.4L17.1 22h-2.7l-3.3-7.4V22H8z"
        fill="white"
      />
    </svg>
  );
}
