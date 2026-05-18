import { useEffect, useMemo, useState, useCallback, memo } from "react";
import { useNavigate } from "react-router-dom";

import {
  Box, Card, Grid, Autocomplete, TextField, Icon,
  Table, TableBody, TableRow, TableCell, TableContainer, TableSortLabel,
  Chip, CircularProgress, Divider, IconButton, Tooltip,
  Menu, MenuItem, ListItemIcon, ListItemText,
} from "@mui/material";
import AbcIcon from "@mui/icons-material/Abc";
import DataObjectIcon from "@mui/icons-material/DataObject";
import FilterListIcon from "@mui/icons-material/FilterList";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import PersonIcon from "@mui/icons-material/Person";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import DownloadIcon from "@mui/icons-material/Download";

import { AdapterMoment } from "@mui/x-date-pickers/AdapterMoment";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";

import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import MDPagination from "components/MDPagination";
import DatabaseLayout from "layouts/DatabaseLayout";

import { SessionController } from "database/session-control";

const TYPE_META = {
  MedtronicBrainSenseTimeDomain: { label: "BrainSense Stream", color: "#1565c0", bg: "#e3f2fd" },
  MedtronicBrainSensePowerDomain: { label: "Power Domain", color: "#4527a0", bg: "#ede7f6" },
  MedtronicChronicBrainSense: { label: "Chronic LFP", color: "#1b5e20", bg: "#e8f5e9" },
  MedtronicBrainSenseSurvey: { label: "Survey", color: "#e65100", bg: "#fff3e0" },
  MedtronicIndefiniteStream: { label: "Indefinite Stream", color: "#006064", bg: "#e0f7fa" },
  MedtronicBaselineMontages: { label: "Baseline Montage", color: "#827717", bg: "#f9fbe7" },
  MedtronicElectrodeIdentifier: { label: "Electrode Identifier", color: "#37474f", bg: "#eceff1" },
  MedtronicDeviceImpedance: { label: "Impedance", color: "#4e342e", bg: "#efebe9" },
  MedtronicStimulationMontages: { label: "Stim Montage", color: "#880e4f", bg: "#fce4ec" },
  PatientControllerEvent: { label: "Patient Event", color: "#bf360c", bg: "#fbe9e7" },
  DelsysMDAT: { label: "Delsys EMG", color: "#1a237e", bg: "#e8eaf6" },
  AOMPX: { label: "AlphaOmega MPX", color: "#311b92", bg: "#ede7f6" },
  MATFile: { label: "MATLAB File", color: "#33691e", bg: "#f1f8e9" },
};

const typeLabel = (t) => TYPE_META[t]?.label || t;
const typeChipSx = (t) => ({
  backgroundColor: TYPE_META[t]?.bg || "#f5f5f5",
  color: TYPE_META[t]?.color || "#333",
  fontWeight: 600,
  fontSize: "11px",
  height: 22,
  mr: 0.5,
  mb: 0.5,
  border: `1px solid ${TYPE_META[t]?.color || "#ccc"}33`,
});

const COL = {
  expand: { width: 36, px: 1 },
  name: {},
  diagnosis: { width: "18%" },
  sex: { width: 70 },
  device: { width: "20%" },
  recordings: { width: 96, align: "center" },
  action: { width: 48, px: 0 },
};

function StatCard({ title, value, subtitle }) {
  return (
    <Card sx={{ height: "100%" }}>
      <MDBox p={2.5}>
        <MDTypography variant="overline" color="text" fontWeight="medium" sx={{ letterSpacing: 1 }}>
          {title}
        </MDTypography>
        <MDTypography variant="h3" fontWeight="bold" mt={0.5} mb={0}>
          {value}
        </MDTypography>
        {subtitle && (
          <MDTypography variant="caption" color="secondary">{subtitle}</MDTypography>
        )}
      </MDBox>
    </Card>
  );
}

const uniqueDeviceTypes = (devices) => [...new Set(devices.map((d) => d.Type))];

const INNER_PAGE_SIZE = 10;

const REC_COLS = [
  { key: "type", label: "Type" },
  { key: "date", label: "Date" },
  { key: "name", label: "Name" },
  { key: "uid",  label: "UUID" },
];

const ExpandableRow = memo(function ExpandableRow({ row, navigate }) {
  const [open, setOpen] = useState(false);
  const [sortCol, setSortCol] = useState("date");
  const [sortDir, setSortDir] = useState("desc");
  const [dlMenu, setDlMenu] = useState(null);
  const [dlTarget, setDlTarget] = useState(null);
  const [visibleCount, setVisibleCount] = useState(INNER_PAGE_SIZE);
  const deviceTypes = uniqueDeviceTypes(row.DBSDevices);

  const visibleRecordings = useMemo(
    () => row.Recordings.filter((r) => TYPE_META[r.type]),
    [row.Recordings]
  );

  const handleSort = (col) => {
    if (col === sortCol) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
  };

  const sortedRecordings = useMemo(() => {
    return [...visibleRecordings].sort((a, b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      if (sortCol === "date") return dir * ((a.date || 0) - (b.date || 0));
      if (sortCol === "uid")  return dir * (a.uid  || "").localeCompare(b.uid  || "");
      if (sortCol === "name") return dir * (a.name || "").localeCompare(b.name || "");
      if (sortCol === "type") return dir * (a.type || "").localeCompare(b.type || "");
      return 0;
    });
  }, [visibleRecordings, sortCol, sortDir]);

  // Reset slice to first page whenever the row opens or sort order changes.
  useEffect(() => { setVisibleCount(INNER_PAGE_SIZE); }, [open, sortCol, sortDir]);

  const displayedRecordings = useMemo(
    () => sortedRecordings.slice(0, visibleCount),
    [sortedRecordings, visibleCount]
  );

  const hasMore = visibleCount < sortedRecordings.length;

  const handleInnerScroll = useCallback((e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 80) {
      setVisibleCount((c) => Math.min(c + INNER_PAGE_SIZE, sortedRecordings.length));
    }
  }, [sortedRecordings.length]);

  return (
    <>
      <TableRow
        hover
        sx={{ cursor: "pointer" }}
        onClick={() => setOpen((v) => !v)}
      >
        <TableCell sx={COL.expand}>
          {open
            ? <ExpandLessIcon fontSize="small" sx={{ color: "text.secondary", display: "block" }} />
            : <ExpandMoreIcon fontSize="small" sx={{ color: "text.secondary", display: "block" }} />}
        </TableCell>
        <TableCell sx={COL.name}>
          <MDTypography variant="button" fontWeight="medium">{row.Name}</MDTypography>
        </TableCell>
        <TableCell sx={COL.diagnosis}>
          <MDTypography variant="caption" color="text">{row.Diagnosis || "—"}</MDTypography>
        </TableCell>
        <TableCell sx={COL.sex}>
          <MDTypography variant="caption" color="text">{row.Sex || "—"}</MDTypography>
        </TableCell>
        <TableCell sx={COL.device}>
          {deviceTypes.map((type) => (
            <Chip
              key={type}
              label={type}
              size="small"
              sx={{ mr: 0.5, mb: 0.25, backgroundColor: "#f3e5f5", color: "#6a1b9a", fontWeight: 600, fontSize: "11px", height: 22 }}
            />
          ))}
        </TableCell>
        <TableCell align={COL.recordings.align} sx={COL.recordings}>
          <MDTypography variant="h6" fontWeight="bold" color="info">{visibleRecordings.length}</MDTypography>
        </TableCell>
        <TableCell sx={COL.action}>
          <Tooltip title="Open participant">
            <IconButton
              size="small"
              onClick={(e) => { e.stopPropagation(); navigate("/participant-overview/" + row.Id); }}
            >
              <OpenInNewIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </TableCell>
      </TableRow>

      {open && (
      <TableRow>
        <TableCell colSpan={7} sx={{ p: 0 }}>
              <MDBox px={2} py={1.5} sx={{
                backgroundColor: "#f8f9fa",
                animation: "bravo-expand 0.18s ease-out",
                "@keyframes bravo-expand": {
                  from: { opacity: 0, transform: "translateY(-6px)" },
                  to:   { opacity: 1, transform: "translateY(0)" },
                },
              }}>
                {row.DBSDevices[0]?.Electrodes?.length > 0 && (
                  <MDBox display="flex" gap={2} flexWrap="wrap" mb={1}>
                    {row.DBSDevices[0].Electrodes.map((e) => (
                      <MDTypography key={e.Id} variant="caption" color="text">
                        <strong>{e.Hemisphere}</strong> · {e.Target} · {e.Type}
                      </MDTypography>
                    ))}
                  </MDBox>
                )}

                <MDTypography variant="overline" color="text" sx={{ letterSpacing: 1 }}>
                  Recordings ({visibleRecordings.length})
                </MDTypography>

                <TableContainer onScroll={handleInnerScroll} sx={{ maxHeight: 300, mt: 0.5, border: "1px solid #e0e0e0", borderRadius: 1, overflow: "auto" }}>
                  <Table size="small" sx={{ width: "100%" }}>
                    <TableBody>
                      <TableRow sx={{ backgroundColor: "#f0f0f0" }}>
                        {REC_COLS.map(({ key, label }) => (
                          <TableCell
                            key={key}
                            sx={{ py: 0.75, backgroundColor: "#f0f0f0", userSelect: "none" }}
                            onClick={(e) => { e.stopPropagation(); handleSort(key); }}
                          >
                            <TableSortLabel
                              active={sortCol === key}
                              direction={sortCol === key ? sortDir : "asc"}
                              sx={{ "& .MuiTableSortLabel-icon": { fontSize: 12 } }}
                            >
                              <MDTypography variant="overline" fontWeight="bold" sx={{ fontSize: "10px", letterSpacing: 0.8 }}>
                                {label}
                              </MDTypography>
                            </TableSortLabel>
                          </TableCell>
                        ))}
                        <TableCell sx={{ py: 0.75, width: 36, backgroundColor: "#f0f0f0" }} />
                      </TableRow>
                      {displayedRecordings.map((r) => (
                        <TableRow key={r.uid} hover>
                          <TableCell sx={{ py: 0.5 }}>
                            <Chip label={typeLabel(r.type)} size="small" sx={typeChipSx(r.type)} />
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <MDTypography variant="caption" color="text">
                              {r.date ? new Date(r.date * 1000).toLocaleString() : "—"}
                            </MDTypography>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <MDTypography
                              variant="caption"
                              color="text"
                              sx={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                            >
                              {r.name || "—"}
                            </MDTypography>
                          </TableCell>
                          <TableCell sx={{ py: 0.5 }}>
                            <Tooltip title={r.uid} placement="left">
                              <MDTypography
                                variant="caption"
                                color="text"
                                sx={{ fontFamily: "monospace", fontSize: "10px", cursor: "default" }}
                              >
                                {r.uid.slice(0, 8)}…
                              </MDTypography>
                            </Tooltip>
                          </TableCell>
                          <TableCell sx={{ py: 0.5, width: 36, px: 0 }}>
                            <Tooltip title="Download CSV">
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setDlTarget(r);
                                  setDlMenu(e.currentTarget);
                                }}
                              >
                                <DownloadIcon sx={{ fontSize: 14 }} />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                      {hasMore && (
                        <TableRow>
                          <TableCell colSpan={5} align="center" sx={{ py: 1, borderBottom: "none" }}>
                            <MDTypography variant="caption" color="secondary">
                              Showing {visibleCount} of {sortedRecordings.length} · scroll for more
                            </MDTypography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </MDBox>
        </TableCell>
      </TableRow>
      )}

      <Menu
        anchorEl={dlMenu}
        open={Boolean(dlMenu)}
        onClose={() => { setDlMenu(null); setDlTarget(null); }}
        onClick={(e) => e.stopPropagation()}
      >
        <MenuItem disabled sx={{ opacity: "1 !important", pb: 0 }}>
          <MDTypography variant="caption" color="secondary" sx={{ fontSize: "10px", letterSpacing: 0.5 }}>
            CHANNEL NAMES
          </MDTypography>
        </MenuItem>
        <MenuItem
          onClick={() => {
            window.open(`/api/queryFilterData?RecordingId=${dlTarget?.uid}&ParticipantId=${row.Id}&ChannelFormat=clean`);
            setDlMenu(null); setDlTarget(null);
          }}
        >
          <ListItemIcon><AbcIcon fontSize="small" /></ListItemIcon>
          <ListItemText
            primary="Clean names"
            secondary="Human-readable electrode labels (e.g. STN Right E00-E01)"
            primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
            secondaryTypographyProps={{ variant: "caption" }}
          />
        </MenuItem>
        <MenuItem
          onClick={() => {
            window.open(`/api/queryFilterData?RecordingId=${dlTarget?.uid}&ParticipantId=${row.Id}&ChannelFormat=raw`);
            setDlMenu(null); setDlTarget(null);
          }}
        >
          <ListItemIcon><DataObjectIcon fontSize="small" /></ListItemIcon>
          <ListItemText
            primary="Raw names"
            secondary="Original device strings (e.g. RIGHT_RING_OR_SEGMENT_ELECTRODE_E00_PLUS_E01_PLUS)"
            primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
            secondaryTypographyProps={{ variant: "caption" }}
          />
        </MenuItem>
      </Menu>
    </>
  );
});

const EMPTY_FILTERS = {
  Diagnosis: [], Tags: [], RecordingTypes: [], Devices: [], Targets: [],
  DateRange: { Start: null, End: null },
};

const VIEW_PER_PAGE = 20;

export default function FilterData() {
  const navigate = useNavigate();
  const [alert, setAlert] = useState(null);

  const [availableOptions, setAvailableOptions] = useState({
    Diagnoses: [], Tags: [], TagCounts: {}, RecordingTypes: [], Devices: [], Targets: [],
  });
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  const [outerSortCol, setOuterSortCol] = useState("name");
  const [outerSortDir, setOuterSortDir] = useState("asc");
  const [paginationControl, setPagination] = useState({ currentPage: 0, totalPages: 0 });
  const [tagInput, setTagInput] = useState("");
  const [downloading, setDownloading] = useState(false);
  const [channelFormat, setChannelFormat] = useState("clean");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      SessionController.query("/api/queryFilterData", { RequestType: "GetFilterOptions" }),
      SessionController.query("/api/queryFilterData", {
        RequestType: "ApplyFilters",
        Filters: { ...EMPTY_FILTERS, DateRange: { Start: null, End: null } },
      }),
    ])
      .then(([optR, resR]) => {
        setAvailableOptions(optR.data);
        setResults(resR.data);
        setSearched(true);
        setLoading(false);
      })
      .catch((e) => { SessionController.displayError(e, setAlert); setLoading(false); });
  }, []);

  const activeFilterCount = [
    filters.Diagnosis, filters.Tags, filters.RecordingTypes, filters.Devices, filters.Targets,
  ].reduce((acc, f) => acc + f.length, 0)
    + (filters.DateRange.Start ? 1 : 0)
    + (filters.DateRange.End ? 1 : 0);

  const handleApply = () => {
    setLoading(true);
    SessionController.query("/api/queryFilterData", {
      RequestType: "ApplyFilters",
      Filters: {
        ...filters,
        DateRange: {
          Start: filters.DateRange.Start ? filters.DateRange.Start.unix() : null,
          End: filters.DateRange.End ? filters.DateRange.End.unix() : null,
        },
      },
    })
      .then((r) => { setResults(r.data); setSearched(true); setLoading(false); })
      .catch((e) => { SessionController.displayError(e, setAlert); setLoading(false); });
  };

  const handleClear = () => {
    setFilters(EMPTY_FILTERS);
    setResults([]);
    setSearched(false);
  };

  const handleOuterSort = (col) => {
    if (col === outerSortCol) setOuterSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setOuterSortCol(col); setOuterSortDir("asc"); }
  };

  const handleDownloadAll = () => {
    setDownloading(true);
    SessionController.query(
      "/api/queryFilterData",
      {
        RequestType: "DownloadAllData",
        ParticipantIds: displayResults.map((p) => p.Id),
        RecordingTypes: filters.RecordingTypes.length > 0 ? filters.RecordingTypes : null,
        ChannelFormat: channelFormat,
      },
      null,
      300000,
      "blob"
    )
      .then((r) => {
        const url = URL.createObjectURL(new Blob([r.data], { type: "text/csv" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = "bravo_all_recordings.csv";
        a.click();
        URL.revokeObjectURL(url);
        setDownloading(false);
      })
      .catch((e) => { SessionController.displayError(e, setAlert); setDownloading(false); });
  };

  const handleExportCSV = () => {
    const header = ["Participant", "Diagnosis", "Sex", "Devices", "Recording Type", "Recording Date", "Recording Name", "Recording UUID"];
    const rows = [];
    for (const p of displayResults) {
      const participantName = p.Name || p.Id || "";
      const devices = uniqueDeviceTypes(p.DBSDevices).join("; ");
      const visible = p.Recordings.filter((r) => TYPE_META[r.type]);
      if (visible.length === 0) {
        rows.push([participantName, p.Diagnosis || "", p.Sex || "", devices, "", "", "", ""]);
      } else {
        for (const rec of visible) {
          rows.push([
            participantName,
            p.Diagnosis || "",
            p.Sex || "",
            devices,
            typeLabel(rec.type),
            rec.date ? new Date(rec.date * 1000).toLocaleString() : "",
            rec.name || "",
            rec.uid,
          ]);
        }
      }
    }
    const csv = [header, ...rows]
      .map((row) => row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "bravo_filter_results.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const displayResults = useMemo(() => {
    return [...results].sort((a, b) => {
      const dir = outerSortDir === "asc" ? 1 : -1;
      if (outerSortCol === "name")       return dir * (a.Name || "").localeCompare(b.Name || "");
      if (outerSortCol === "diagnosis")  return dir * (a.Diagnosis || "").localeCompare(b.Diagnosis || "");
      if (outerSortCol === "recordings") return dir * (a.Recordings.length - b.Recordings.length);
      return 0;
    });
  }, [results, outerSortCol, outerSortDir]);

  useEffect(() => {
    setPagination({
      currentPage: 0,
      totalPages: Math.ceil(displayResults.length / VIEW_PER_PAGE),
    });
  }, [displayResults]);

  const pagedResults = useMemo(() => {
    const start = paginationControl.currentPage * VIEW_PER_PAGE;
    return displayResults.slice(start, start + VIEW_PER_PAGE);
  }, [displayResults, paginationControl.currentPage]);

  const handlePageChange = (page) => {
    if (page >= 0 && page < paginationControl.totalPages) {
      setPagination((p) => ({ ...p, currentPage: page }));
    }
  };

  const pageItems = useMemo(() => {
    const { currentPage, totalPages } = paginationControl;
    const range = (start, len) => Array.from({ length: len }, (_, i) => start + i);
    let pages;
    if (totalPages <= 8) {
      pages = range(0, totalPages);
    } else if (currentPage < 4) {
      pages = range(0, 8);
    } else if (currentPage < totalPages - 4) {
      pages = range(currentPage - 4, 8);
    } else {
      pages = range(totalPages - 8, 8);
    }
    return pages.map((p) => (
      <MDPagination key={p} item onClick={() => handlePageChange(p)} active={p === currentPage}>
        {p + 1}
      </MDPagination>
    ));
  }, [paginationControl]);

  const totalRecordings = displayResults.reduce((acc, p) => acc + p.Recordings.filter(r => TYPE_META[r.type]).length, 0);
  const uniqueTypes = [...new Set(
    displayResults.flatMap((p) => p.Recordings.filter(r => TYPE_META[r.type]).map((r) => r.type))
  )];

  return (
    <DatabaseLayout>
      {alert}

      <MDBox mt={2} mb={2} display="flex" alignItems="center" gap={1}>
        <FilterListIcon sx={{ color: "info.main" }} />
        <MDTypography variant="h5" fontWeight="bold">Filter Data</MDTypography>
        {activeFilterCount > 0 && (
          <Chip label={`${activeFilterCount} active`} size="small" color="info" sx={{ fontWeight: 700 }} />
        )}
        {loading && <CircularProgress size={18} sx={{ ml: 1 }} />}
      </MDBox>

      {/* Filter Panel */}
      <Card sx={{ mb: 3 }}>
        <MDBox p={3}>
          <MDTypography variant="overline" color="text" sx={{ letterSpacing: 1, mb: 1, display: "block" }}>
            Participant
          </MDTypography>
          <Grid container spacing={2} mb={2}>
            <Grid item xs={12} md={3}>
              <Autocomplete
                multiple
                options={availableOptions.Diagnoses}
                value={filters.Diagnosis}
                onChange={(_, v) => setFilters({ ...filters, Diagnosis: v })}
                renderInput={(p) => <TextField {...p} label="Diagnosis" size="small" />}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Autocomplete
                multiple
                options={availableOptions.Devices}
                value={filters.Devices}
                onChange={(_, v) => setFilters({ ...filters, Devices: v })}
                renderInput={(p) => <TextField {...p} label="Device Type" size="small" />}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Autocomplete
                multiple
                options={availableOptions.Targets}
                value={filters.Targets}
                onChange={(_, v) => setFilters({ ...filters, Targets: v })}
                renderInput={(p) => <TextField {...p} label="Electrode Target" size="small" />}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Autocomplete
                multiple
                options={availableOptions.Tags}
                value={filters.Tags}
                inputValue={tagInput}
                onInputChange={(_, v) => setTagInput(v)}
                filterOptions={(opts, { inputValue }) =>
                  inputValue.length < 3
                    ? []
                    : opts.filter((o) => o.toLowerCase().includes(inputValue.toLowerCase()))
                }
                noOptionsText={tagInput.length < 3 ? "Type 3+ characters to search" : "No tags found"}
                onChange={(_, v) => setFilters({ ...filters, Tags: v })}
                renderOption={(props, opt) => (
                  <li {...props}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" width="100%">
                      <span>{opt}</span>
                      {availableOptions.TagCounts?.[opt] != null && (
                        <Chip
                          label={availableOptions.TagCounts[opt]}
                          size="small"
                          sx={{ ml: 1, height: 18, fontSize: "10px", pointerEvents: "none" }}
                        />
                      )}
                    </Box>
                  </li>
                )}
                renderInput={(p) => <TextField {...p} label="Tags" size="small" />}
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 2 }} />

          <MDTypography variant="overline" color="text" sx={{ letterSpacing: 1, mb: 1, display: "block" }}>
            Recordings
          </MDTypography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Autocomplete
                multiple
                options={availableOptions.RecordingTypes}
                value={filters.RecordingTypes}
                getOptionLabel={(opt) => typeLabel(opt)}
                onChange={(_, v) => setFilters({ ...filters, RecordingTypes: v })}
                renderOption={(props, opt) => (
                  <li {...props}>
                    <Chip label={typeLabel(opt)} size="small" sx={{ ...typeChipSx(opt), pointerEvents: "none" }} />
                  </li>
                )}
                renderInput={(p) => <TextField {...p} label="Recording Type" size="small" />}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <LocalizationProvider dateAdapter={AdapterMoment}>
                <DatePicker
                  label="From"
                  value={filters.DateRange.Start}
                  onChange={(v) => setFilters({ ...filters, DateRange: { ...filters.DateRange, Start: v } })}
                  renderInput={(p) => <TextField {...p} size="small" fullWidth />}
                />
              </LocalizationProvider>
            </Grid>
            <Grid item xs={12} md={3}>
              <LocalizationProvider dateAdapter={AdapterMoment}>
                <DatePicker
                  label="To"
                  value={filters.DateRange.End}
                  onChange={(v) => setFilters({ ...filters, DateRange: { ...filters.DateRange, End: v } })}
                  renderInput={(p) => <TextField {...p} size="small" fullWidth />}
                />
              </LocalizationProvider>
            </Grid>
          </Grid>

          <MDBox mt={2.5} display="flex" alignItems="center" gap={1}>
            <MDButton
              variant="gradient"
              color="info"
              onClick={handleApply}
              disabled={loading}
              sx={{ minWidth: 140 }}
            >
              {loading ? <CircularProgress size={16} color="inherit" /> : "Apply Filters"}
            </MDButton>
            <MDButton variant="outlined" color="secondary" onClick={handleClear}>Clear</MDButton>
          </MDBox>
        </MDBox>
      </Card>

      {/* Stats + Results */}
      {searched && (
        <>
          <Grid container spacing={2} mb={3}>
            <Grid item xs={6} md={3}>
              <StatCard title="Participants" value={displayResults.length} subtitle="matched" />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard title="Total Recordings" value={totalRecordings} subtitle="across all participants" />
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ height: "100%" }}>
                <MDBox p={2.5}>
                  <MDTypography variant="overline" color="text" sx={{ letterSpacing: 1 }}>
                    Recording Types Present
                  </MDTypography>
                  <MDBox mt={1} display="flex" flexWrap="wrap">
                    {uniqueTypes.map((t) => (
                      <Chip key={t} label={typeLabel(t)} size="small" sx={typeChipSx(t)} />
                    ))}
                  </MDBox>
                </MDBox>
              </Card>
            </Grid>
          </Grid>

          <Card>
            <MDBox px={3} pt={2.5} pb={1} display="flex" alignItems="center" gap={1}>
              <PersonIcon sx={{ color: "info.main" }} />
              <MDTypography variant="h6" fontWeight="bold">
                {displayResults.length} Participant{displayResults.length !== 1 ? "s" : ""}
              </MDTypography>
              <MDTypography variant="caption" color="secondary" ml={1}>
                Click a row to expand · click the arrow icon to open the participant
              </MDTypography>
              <Box flex={1} />
              <Tooltip title="Export metadata for visible results as CSV">
                <span>
                  <MDButton
                    variant="outlined"
                    color="info"
                    size="small"
                    startIcon={<FileDownloadIcon />}
                    onClick={handleExportCSV}
                    disabled={displayResults.length === 0}
                  >
                    Export CSV
                  </MDButton>
                </span>
              </Tooltip>
              <Tooltip
                title={
                  channelFormat === "clean"
                    ? "Clean names: human-readable electrode labels (e.g. STN Right E00-E01)"
                    : "Raw names: original device strings (e.g. RIGHT_RING_OR_SEGMENT_ELECTRODE_E00_PLUS_E01_PLUS)"
                }
              >
                <Chip
                  label={channelFormat === "clean" ? "Clean names" : "Raw names"}
                  size="small"
                  icon={channelFormat === "clean" ? <AbcIcon sx={{ fontSize: "14px !important" }} /> : <DataObjectIcon sx={{ fontSize: "14px !important" }} />}
                  onClick={() => setChannelFormat((f) => f === "clean" ? "raw" : "clean")}
                  sx={{ cursor: "pointer", fontWeight: 600, fontSize: "11px", height: 28 }}
                />
              </Tooltip>
              <Tooltip title="Download all recording data as one combined CSV (may be large)">
                <span>
                  <MDButton
                    variant="gradient"
                    color="info"
                    size="small"
                    startIcon={downloading ? <CircularProgress size={14} color="inherit" /> : <DownloadIcon />}
                    onClick={handleDownloadAll}
                    disabled={displayResults.length === 0 || downloading}
                  >
                    {downloading ? "Downloading…" : "Download All Data"}
                  </MDButton>
                </span>
              </Tooltip>
            </MDBox>

            <TableContainer sx={{ width: "100%", px: 5, py: 1 }}>
              <Table sx={{ width: "100%", minWidth: "100%" }}>
                <TableBody>
                  <TableRow sx={{ backgroundColor: "#f8f9fa" }}>
                    <TableCell sx={COL.expand} />
                    <TableCell sx={COL.name}>
                      <TableSortLabel
                        active={outerSortCol === "name"}
                        direction={outerSortCol === "name" ? outerSortDir : "asc"}
                        onClick={() => handleOuterSort("name")}
                        sx={{ "& .MuiTableSortLabel-icon": { fontSize: 12 } }}
                      >
                        <MDTypography variant="overline" fontWeight="bold" color="text" sx={{ letterSpacing: 0.8 }}>Name</MDTypography>
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sx={COL.diagnosis}>
                      <TableSortLabel
                        active={outerSortCol === "diagnosis"}
                        direction={outerSortCol === "diagnosis" ? outerSortDir : "asc"}
                        onClick={() => handleOuterSort("diagnosis")}
                        sx={{ "& .MuiTableSortLabel-icon": { fontSize: 12 } }}
                      >
                        <MDTypography variant="overline" fontWeight="bold" color="text" sx={{ letterSpacing: 0.8 }}>Diagnosis</MDTypography>
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sx={COL.sex}>
                      <MDTypography variant="overline" fontWeight="bold" color="text" sx={{ letterSpacing: 0.8 }}>Sex</MDTypography>
                    </TableCell>
                    <TableCell sx={COL.device}>
                      <MDTypography variant="overline" fontWeight="bold" color="text" sx={{ letterSpacing: 0.8 }}>Device</MDTypography>
                    </TableCell>
                    <TableCell align={COL.recordings.align} sx={COL.recordings}>
                      <TableSortLabel
                        active={outerSortCol === "recordings"}
                        direction={outerSortCol === "recordings" ? outerSortDir : "asc"}
                        onClick={() => handleOuterSort("recordings")}
                        sx={{ "& .MuiTableSortLabel-icon": { fontSize: 12 } }}
                      >
                        <MDTypography variant="overline" fontWeight="bold" color="text" sx={{ letterSpacing: 0.8 }}>Recordings</MDTypography>
                      </TableSortLabel>
                    </TableCell>
                    <TableCell sx={COL.action} />
                  </TableRow>
                  {pagedResults.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                        <MDTypography variant="body2" color="secondary">
                          No participants match the selected filters.
                        </MDTypography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    pagedResults.map((row) => (
                      <ExpandableRow key={row.Id} row={row} navigate={navigate} />
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            {paginationControl.totalPages > 1 && (
              <MDBox display="flex" justifyContent="space-between" alignItems="center" px={3} pb={2}>
                <MDTypography variant="caption" color="secondary">
                  Showing {paginationControl.currentPage * VIEW_PER_PAGE + 1}–
                  {Math.min((paginationControl.currentPage + 1) * VIEW_PER_PAGE, displayResults.length)} of {displayResults.length}
                </MDTypography>
                <MDPagination variant="gradient" color="info">
                  <MDPagination item onClick={() => handlePageChange(paginationControl.currentPage - 1)}>
                    <Icon sx={{ fontWeight: "bold" }}>chevron_left</Icon>
                  </MDPagination>
                  {pageItems}
                  <MDPagination item onClick={() => handlePageChange(paginationControl.currentPage + 1)}>
                    <Icon sx={{ fontWeight: "bold" }}>chevron_right</Icon>
                  </MDPagination>
                </MDPagination>
              </MDBox>
            )}
          </Card>
        </>
      )}
    </DatabaseLayout>
  );
}
