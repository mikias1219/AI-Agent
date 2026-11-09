export default function PageHeading({ eyebrow, title, children, action }) {
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div>
        {eyebrow && <p className="eyebrow mb-1.5">{eyebrow}</p>}
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{title}</h1>
        {children && <p className="mt-1.5 max-w-xl text-sm leading-6 text-slate-500">{children}</p>}
      </div>
      {action}
    </div>
  );
}
