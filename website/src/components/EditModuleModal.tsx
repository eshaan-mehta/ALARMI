import { useEffect } from 'react';
import {
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  TextInput,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import { isAxiosError } from 'axios';
import { useUpdateModule } from '../data/designs/hooks';
import type { Module, ModulePatch } from '../data/designs/types';

const MODULE_TYPE_OPTIONS = [
  'Wall Panel',
  'Bathroom Service Wall',
  'Hospital Headwall',
  'Utility Panel',
];
const UNIT_SCALE_OPTIONS = ['METRE', 'MILLIMETRE', 'CENTIMETRE', 'FOOT', 'INCH'];

/** Metres per 1 of each unit — the basis for converting dimensions between units. */
const METRES_PER_UNIT: Record<string, number> = {
  METRE: 1,
  MILLIMETRE: 0.001,
  CENTIMETRE: 0.01,
  FOOT: 0.3048,
  INCH: 0.0254,
};

/** Short label shown in each dimension field's bracket, e.g. "Width x (cm)". */
const UNIT_ABBR: Record<string, string> = {
  METRE: 'm',
  MILLIMETRE: 'mm',
  CENTIMETRE: 'cm',
  FOOT: 'ft',
  INCH: 'in',
};

/** Convert a length from one unit to another; trims float noise to 4 decimals. */
function convertLength(value: number, from: string, to: string): number {
  const f = METRES_PER_UNIT[from];
  const t = METRES_PER_UNIT[to];
  if (!f || !t) return value;
  return Math.round((value * f) / t * 1e4) / 1e4;
}

interface Props {
  module: Module;
  designId: string;
  opened: boolean;
  onClose: () => void;
}

interface FormValues {
  type: string;
  dimX: number | string;
  dimY: number | string;
  dimZ: number | string;
  roomId: string;
  unitScale: string;
}

function valuesFromModule(m: Module): FormValues {
  return {
    type: m.type ?? '',
    dimX: m.dimensions?.x ?? 0,
    dimY: m.dimensions?.y ?? 0,
    dimZ: m.dimensions?.z ?? 0,
    roomId: m.roomId ?? '',
    unitScale: m.unitScale ?? '',
  };
}

export function EditModuleModal({ module, designId, opened, onClose }: Props) {
  const update = useUpdateModule(designId);

  const form = useForm<FormValues>({
    initialValues: valuesFromModule(module),
  });

  // Re-seed the form with the latest values each time the modal opens.
  useEffect(() => {
    if (opened) form.setValues(valuesFromModule(module));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opened]);

  const handleClose = () => {
    if (update.isPending) return;
    onClose();
  };

  const unitAbbr = UNIT_ABBR[form.values.unitScale] ?? '';

  // Switching units re-scales the current dimension values (frontend only) and
  // relabels the fields; the chosen unit + converted values are what get saved.
  const handleUnitChange = (next: string | null) => {
    if (!next) return;
    const prev = form.values.unitScale;
    if (prev && next !== prev) {
      form.setValues({
        unitScale: next,
        dimX: convertLength(Number(form.values.dimX) || 0, prev, next),
        dimY: convertLength(Number(form.values.dimY) || 0, prev, next),
        dimZ: convertLength(Number(form.values.dimZ) || 0, prev, next),
      });
    } else {
      form.setFieldValue('unitScale', next);
    }
  };

  const handleSubmit = form.onSubmit((values) => {
    const patch: ModulePatch = {
      type: values.type || undefined,
      dimensions: {
        x: Number(values.dimX) || 0,
        y: Number(values.dimY) || 0,
        z: Number(values.dimZ) || 0,
      },
      roomId: values.roomId || undefined,
      unitScale: values.unitScale || undefined,
    };

    update.mutate(
      { moduleId: module.moduleId, patch },
      {
        onSuccess: () => {
          notifications.show({
            color: 'teal',
            title: 'Module updated',
            message: 'Metadata saved.',
          });
          onClose();
        },
        onError: (err) => {
          const message = isAxiosError(err)
            ? (err.response?.data?.message ?? 'Could not save changes.')
            : 'Could not save changes.';
          notifications.show({ color: 'red', title: 'Update failed', message });
        },
      },
    );
  });

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Edit module metadata"
      centered
      closeOnClickOutside={!update.isPending}
    >
      <form onSubmit={handleSubmit}>
        <Stack>
          <Select
            label="Type"
            data={MODULE_TYPE_OPTIONS}
            searchable
            {...form.getInputProps('type')}
          />
          <Group grow>
            <NumberInput
              label={`Width x (${unitAbbr})`}
              min={0}
              step={0.1}
              decimalScale={4}
              {...form.getInputProps('dimX')}
            />
            <NumberInput
              label={`Height y (${unitAbbr})`}
              min={0}
              step={0.1}
              decimalScale={4}
              {...form.getInputProps('dimY')}
            />
            <NumberInput
              label={`Depth z (${unitAbbr})`}
              min={0}
              step={0.1}
              decimalScale={4}
              {...form.getInputProps('dimZ')}
            />
          </Group>
          <Group grow>
            <TextInput label="Room ID" {...form.getInputProps('roomId')} />
            <Select
              label="Unit scale"
              data={UNIT_SCALE_OPTIONS}
              allowDeselect={false}
              value={form.values.unitScale}
              onChange={handleUnitChange}
              error={form.errors.unitScale}
            />
          </Group>

          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose} disabled={update.isPending}>
              Cancel
            </Button>
            <Button type="submit" loading={update.isPending}>
              Save changes
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
