import React from 'react';
import {
  Box,
  Button,
  HStack,
  IconButton,
  MenuRoot,
  MenuTrigger,
  MenuContent,
  MenuItem,
  Text,
} from '@chakra-ui/react';
import { FiChevronLeft, FiChevronRight, FiMoreHorizontal } from 'react-icons/fi';

type Props = {
  page: number; // 1-based
  pageSize: number;
  total: number;
  pageSizeOptions?: number[];
  onPageChange: (page: number) => void; // 1-based
  onPageSizeChange: (pageSize: number) => void;
};

const defaultPageSizes = [10, 25, 50, 100];

const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(max, n));

const rangeLabel = (page: number, pageSize: number, total: number) => {
  if (total <= 0) return '0–0 of 0';
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);
  return `${start}–${end} of ${total}`;
};

const buildPageItems = (page: number, totalPages: number) => {
  // Always show: 1, last, current±1; collapse with ellipses when needed.
  const p = clamp(page, 1, totalPages);
  const visible = new Set<number>([1, totalPages, p, p - 1, p + 1, p - 2, p + 2].filter((x) => x >= 1 && x <= totalPages));
  const sorted = Array.from(visible).sort((a, b) => a - b);

  const out: Array<number | 'ellipsis'> = [];
  for (let i = 0; i < sorted.length; i++) {
    const cur = sorted[i];
    const prev = sorted[i - 1];
    if (i > 0 && prev !== undefined && cur - prev > 1) out.push('ellipsis');
    out.push(cur);
  }
  // Defensive de-dupe: ensure no duplicate numbers ever render (helps with edge cases).
  const finalOut: Array<number | 'ellipsis'> = [];
  const seenNum = new Set<number>();
  for (const it of out) {
    if (it === 'ellipsis') {
      if (finalOut[finalOut.length - 1] !== 'ellipsis') finalOut.push('ellipsis');
      continue;
    }
    if (seenNum.has(it)) continue;
    seenNum.add(it);
    finalOut.push(it);
  }
  return finalOut;
};

export default function Pagination({
  page,
  pageSize,
  total,
  pageSizeOptions = defaultPageSizes,
  onPageChange,
  onPageSizeChange,
}: Props) {
  const totalPages = Math.max(1, Math.ceil((total || 0) / pageSize));
  const safePage = clamp(page, 1, totalPages);
  const items = buildPageItems(safePage, totalPages);

  return (
    <HStack justify="space-between" gap={3} flexWrap="wrap" w="full">
      <Text fontSize="xs" color="fg.muted">
        {rangeLabel(safePage, pageSize, total || 0)}
      </Text>

      <HStack gap={2} flexWrap="wrap" justify="flex-end">
        <IconButton
          aria-label="Previous page"
          size="sm"
          variant="outline"
          disabled={safePage <= 1}
          onClick={() => onPageChange(safePage - 1)}
        >
          <FiChevronLeft />
        </IconButton>

        <HStack gap={1}>
          {items.map((it, idx) =>
            it === 'ellipsis' ? (
              <Box key={`e-${idx}`} px={2} color="fg.muted" display="flex" alignItems="center">
                <FiMoreHorizontal />
              </Box>
            ) : (
              <Button
                key={it}
                size="sm"
                variant={it === safePage ? 'solid' : 'outline'}
                onClick={() => onPageChange(it)}
                minW="36px"
              >
                {it}
              </Button>
            ),
          )}
        </HStack>

        <IconButton
          aria-label="Next page"
          size="sm"
          variant="outline"
          disabled={safePage >= totalPages}
          onClick={() => onPageChange(safePage + 1)}
        >
          <FiChevronRight />
        </IconButton>

        <MenuRoot>
          <MenuTrigger asChild>
            <Button size="sm" variant="outline" aria-label="Page size">
              {pageSize} / page
            </Button>
          </MenuTrigger>
          <MenuContent>
            {pageSizeOptions.map((opt) => (
              <MenuItem
                key={opt}
                value={String(opt)}
                onClick={() => onPageSizeChange(opt)}
              >
                {opt} per page
              </MenuItem>
            ))}
          </MenuContent>
        </MenuRoot>
      </HStack>
    </HStack>
  );
}


