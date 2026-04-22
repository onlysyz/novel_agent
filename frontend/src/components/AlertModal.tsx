import { useTranslation } from "../i18n";

interface Props {
  message: string;
  onClose: () => void;
}

export default function AlertModal({ message, onClose }: Props) {
  const { t } = useTranslation();

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-icon">⚠️</div>
        <p className="modal-message">{message}</p>
        <button className="btn-primary" onClick={onClose}>
          {t("ok") || "OK"}
        </button>
      </div>
    </div>
  );
}
