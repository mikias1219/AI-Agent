import { appList } from '../../config/app-catalog.js';

export default function AppMark({ id, size = 'size-10' }) {
  const app = appList.find((a) => a.id === id);
  return (
    <span
      aria-hidden="true"
      className={`${size} ${app.color} inline-grid shrink-0 place-items-center rounded-xl text-lg font-bold`}
    >
      {app.mark}
    </span>
  );
}
