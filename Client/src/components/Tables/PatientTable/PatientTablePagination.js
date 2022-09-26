import { useEffect, useState } from "react";

import {
  Icon
} from "@mui/material";

import MDTypography from "components/MDTypography";
import MDBox from "components/MDBox";
import MDPagination from "components/MDPagination";

import { dictionary } from "assets/translation";
import { usePlatformContext } from "context";

export default function PatientTablePagination({totalCount, totalPages, currentPage, setPagination}) {
  const [controller, ] = usePlatformContext();
  const { language } = controller;

  const handlePageChange = (page) => {
    if (page >= 0 && page < totalPages) {
      setPagination({
        totalPages: totalPages,
        currentPage: page,
      });
    }
  };

  const [pageItems, setPageItems] = useState([]);
  useEffect(() => {
    if (totalPages > 8) {
      if (currentPage < 4) {
        setPageItems(Array.from({length: 8}, (v, i) => i).map((page) => {
          const pageID = page;
          return (
            <MDPagination
              item
              key={pageID}
              onClick={() => handlePageChange(pageID)}
              active={pageID==currentPage}
            >
              {pageID+1}
            </MDPagination>
          );
        }));
      } else if (currentPage < totalPages-4) {
        setPageItems(Array.from({length: 8}, (v, i) => i-4).map((page) => {
          const pageID = currentPage+page;
          return (
            <MDPagination
              item
              key={pageID}
              onClick={() => handlePageChange(pageID)}
              active={pageID==currentPage}
            >
              {pageID+1}
            </MDPagination>
          );
        }));
      } else {
        setPageItems(Array.from({length: 8}, (v, i) => i).map((page) => {
          const pageID = totalPages-8+page;
          return (
            <MDPagination
              item
              key={pageID}
              onClick={() => handlePageChange(pageID)}
              active={pageID==currentPage}
            >
              {pageID+1}
            </MDPagination>
          );
        }));
      }
    } else {
      setPageItems(Array.from({length: totalPages}, (v, i) => i).map((page) => {
        const pageID = page;
        return (
          <MDPagination
            item
            key={pageID}
            onClick={() => handlePageChange(pageID)}
            active={pageID==currentPage}
          >
            {pageID+1}
          </MDPagination>
        );
      }));
    }
  }, [totalPages, currentPage]);
  
  return <MDBox
    display="flex"
    flexDirection={{ xs: "column", sm: "row" }}
    justifyContent="space-between"
    alignItems={{ xs: "flex-start", sm: "center" }}
    p={3}
  >
    <MDBox mb={{ xs: 3, sm: 0 }}>
      <MDTypography variant={"h6"} fontSize={15}>
        {dictionary.Dashboard.SearchResult[language] + totalCount.toString()}
      </MDTypography>
    </MDBox>
    {totalPages > 1 && (
      <MDPagination
        variant={"gradient"}
        color={"info"}
      >
        <MDPagination item onClick={() => {}}>
          <Icon sx={{ fontWeight: "bold" }}>chevron_left</Icon>
        </MDPagination>
        {pageItems}
        <MDPagination item onClick={() => {}}>
          <Icon sx={{ fontWeight: "bold" }}>chevron_right</Icon>
        </MDPagination>
      </MDPagination>
    )}
  </MDBox>
};