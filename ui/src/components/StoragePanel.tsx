import React, { useState, type ChangeEvent } from "react";
import { api } from "../services/api";
import type { SavedMappingItem } from "../types";

interface Props {
  fileId: string;
  hasHeader: boolean;
  mapping: Record<string, string>;
  savedMappings: SavedMappingItem[];
  onRefreshMappings: () => Promise<void>;
  onApplyMapping: (newMapping: Record<string, string>) => void;
}

export const StoragePanel: React.FC<Props> = ({
  fileId,
  hasHeader,
  mapping,
  savedMappings,
  onRefreshMappings,
  onApplyMapping,
}) => {
  const [mappingName, setMappingName] = useState<string>("");
  const [saveResult, setSaveResult] = useState<string>("");
  const [saveClass, setSaveClass] = useState<string>("");
  const [selectedId, setSelectedId] = useState<string>("");

  const handleSaveMapping = async () => {
    const mappingToSave = Object.fromEntries(
      Object.entries(mapping).filter(([_, v]) => v != null && v !== ""),
    );
    const name = mappingName.trim() || "Unnamed mapping";

    try {
      const saved = await api.saveMapping(name, mappingToSave);
      setSaveResult(`Saved mapping "${saved.name}"`);
      setSaveClass("success");
      await onRefreshMappings();
    } catch (err: any) {
      console.error(err);
      setSaveResult(err.message || "Failed to save mapping.");
      setSaveClass("error");
    }
  };

  const handleSaveData = async () => {
    const mappingToSave = Object.fromEntries(
      Object.entries(mapping).filter(([_, v]) => v != null && v !== ""),
    );
    try {
      const saved = await api.saveData(fileId, hasHeader, mappingToSave);
      setSaveResult(`Saved records: "${saved} rows inserted."`);
      setSaveClass("success");
      await onRefreshMappings();
    } catch (err: any) {
      console.error(err);
      setSaveResult(err.message || "Failed to save data.");
      setSaveClass("error");
    }
  };

  const handleLoad = async (event: ChangeEvent<HTMLSelectElement>) => {
    const id = event.target.value;
    setSelectedId(id);
    if (!id) return;

    try {
      const data = await api.fetchSingleMapping(id);
      onApplyMapping(data.mapping || {});
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <>
      <input
        className="form-control"
        type="text"
        placeholder="Enter the mapping name to save"
        value={mappingName}
        onChange={(e) => setMappingName(e.target.value)}
      />
      <button
        className="btn btn-primary"
        type="button"
        onClick={handleSaveMapping}
      >
        Save Mapping
      </button>
      <button
        className="btn btn-primary"
        type="button"
        onClick={handleSaveData}
      >
        Save Mapped CSV Data to DB
      </button>
      <div className={saveClass} style={{ marginTop: "0.5rem" }}>
        {saveResult}
      </div>
      <label
        htmlFor="saved-mappings"
        style={{ marginTop: "1rem", display: "block" }}
      >
        Load Saved Mapping:
      </label>
      <select
        className="form-control form-select"
        value={selectedId}
        onChange={handleLoad}
      >
        <option value="">-- Select saved mapping --</option>
        {savedMappings.map((item) => (
          <option key={item.id} value={String(item.id)}>
            {item.name}
          </option>
        ))}
      </select>
    </>
  );
};
